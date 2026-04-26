"""Reconciliation pipeline orchestrator.

Calls adapters in sequence, applies pure-function services, and assembles the
final ``ReconciliationResponse``. Hard failures (patient not found, FHIR
unreachable) raise custom exceptions — the API route maps these to HTTP status
codes. Soft failures (allergy CSV unavailable, LLM unavailable) degrade
gracefully with explicit status fields in the response.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from app.adapters import allergy_reader, drugbank_client, fhir_client, llm_client
from app.adapters.prompts.system_prompt import SYSTEM_PROMPT_HASH
from app.models.patient_context import MedicationItem, PrescriptionItem
from app.models.request import ReconciliationRequest
from app.models.response import (
    AuditInfo,
    InteractionResult,
    ProcessedInteraction,
    ReconciliationResponse,
    ValidationFlag,
)
from app.services import (
    allergy_checker,
    contraindication_overlay,
    severity_mapper,
    summary_validator,
)

_AI_DISCLAIMER = "This summary was generated with AI assistance and is pending physician review."
_ALLERGY_UNAVAILABLE_REASON = (
    "The allergy data source could not be read. "
    "Please confirm allergies with the patient before approving this prescription."
)
_SUMMARY_UNAVAILABLE_REASON = (
    "The clinical summary service was unavailable. "
    "Deterministic interaction and allergy data is shown."
)


class PatientNotFoundError(Exception):
    """Raised when the patient ID is not found in the FHIR registry."""


class FHIRUnavailableError(Exception):
    """Raised when the FHIR system raises an unexpected error during data fetch."""


def reconcile(request: ReconciliationRequest) -> ReconciliationResponse:
    """Run the full medication reconciliation pipeline for the given request.

    Raises:
        PatientNotFoundError: when the patient ID is not found in FHIR.
        FHIRUnavailableError: when the FHIR system is unreachable or returns an error.
    """
    patient_id = request.patient_id
    new_rx = request.new_prescription

    # 1. Fetch patient — hard fail if not found or FHIR unreachable.
    try:
        patient = fhir_client.get_patient(patient_id)
    except Exception as exc:
        raise FHIRUnavailableError("The clinical records system is currently unavailable.") from exc
    if patient is None:
        raise PatientNotFoundError(
            f"The patient identifier '{patient_id}' was not found in the records system."
        )

    # 2. Pregnancy status — loud failure on unrecognized value is intentional.
    pregnancy_status = fhir_client.get_pregnancy_status(patient_id)
    effective_pregnancy_status = pregnancy_status or "not_pregnant"

    # 3. Fetch active medications — hard fail if FHIR unreachable.
    try:
        active_medications: list[MedicationItem] = fhir_client.get_active_medications_as_items(
            patient_id
        )
    except Exception as exc:
        raise FHIRUnavailableError("The clinical records system is currently unavailable.") from exc

    # 4. Fetch allergies — degraded path on any failure.
    allergies, allergy_status = allergy_reader.get_patient_allergies_safe(patient_id)
    allergy_data_reason = _ALLERGY_UNAVAILABLE_REASON if allergy_status == "unavailable" else None

    # 5–6. Check each active medication for a drug-drug interaction with the new prescription.
    interactions: list[InteractionResult] = []
    for active_med in active_medications:
        record = drugbank_client.check_interaction(active_med.rxnorm_code, new_rx.rxnorm_code)
        if record is None:
            continue
        clinical_severity = severity_mapper.map_severity(record.drugbank_severity)
        clinical_severity = contraindication_overlay.maybe_promote_for_pregnancy(
            clinical_severity, new_rx.rxnorm_code, effective_pregnancy_status
        )
        interactions.append(
            InteractionResult(
                medication_a=record.drug_a.name,
                medication_a_rxnorm=record.drug_a.rxnorm_code,
                medication_b=record.drug_b.name,
                medication_b_rxnorm=record.drug_b.rxnorm_code,
                severity=clinical_severity,
                source_severity=record.drugbank_severity,
                source="drugbank",
                description=record.description,
            )
        )

    pairs_checked = len(active_medications)

    # 7. Check allergy conflicts.
    allergy_conflicts = allergy_checker.check_allergy_conflicts(allergies, new_rx.drug_name)

    # 8. Build ProcessedInteraction list for the LLM call.
    processed_interactions = [
        ProcessedInteraction(
            medication_a=r.medication_a,
            medication_b=r.medication_b,
            severity=r.severity,
            source_severity=r.source_severity,
            description=r.description,
        )
        for r in interactions
    ]

    # 9. Generate clinical summary — degraded path on failure.
    llm_output = llm_client.generate_clinical_summary(
        patient_id=patient_id,
        new_prescription=PrescriptionItem(
            drug_name=new_rx.drug_name,
            rxnorm_code=new_rx.rxnorm_code,
            dosage=new_rx.dosage,
            prescriber_id=new_rx.prescriber_id,
        ),
        active_medications=active_medications,
        interactions=processed_interactions,
        allergy_conflicts=allergy_conflicts,
        allergy_data_status=allergy_status,
        pregnancy_status=effective_pregnancy_status,
    )

    # 10. Validate summary if present; otherwise degrade.
    audit: AuditInfo | None = None
    validation_flags: list[ValidationFlag] = []
    summary_status: Literal["generated", "unavailable"]
    summary_status_reason: str | None

    if llm_output is not None:
        known_names = [new_rx.drug_name] + [m.drug_name for m in active_medications]
        known_codes = [new_rx.rxnorm_code] + [m.rxnorm_code for m in active_medications]
        validation_flags, validation_status = summary_validator.validate_llm_output(
            llm_output, known_names, known_codes, processed_interactions
        )
        audit = AuditInfo(
            model=llm_output.model_identifier,
            prompt_hash=SYSTEM_PROMPT_HASH,
            temperature=int(llm_client.TEMPERATURE),
            validation_status=validation_status,
            generated_at=datetime.now(UTC).isoformat(),
        )
        summary_status = "generated"
        summary_status_reason = None
    else:
        summary_status = "unavailable"
        summary_status_reason = _SUMMARY_UNAVAILABLE_REASON

    # 11. Assemble and return.
    return ReconciliationResponse(
        reconciliation_id=str(uuid.uuid4()),
        patient_id=patient_id,
        timestamp=datetime.now(UTC).isoformat(),
        new_prescription=new_rx,
        active_medications=active_medications,
        pairs_checked=pairs_checked,
        interactions=interactions,
        allergy_conflicts=allergy_conflicts,
        allergy_data_status=allergy_status,
        allergy_data_reason=allergy_data_reason,
        clinical_summary=llm_output.clinical_summary if llm_output is not None else None,
        summary_status=summary_status,
        summary_status_reason=summary_status_reason,
        validation_flags=validation_flags,
        ai_disclaimer=_AI_DISCLAIMER,
        audit=audit,
    )
