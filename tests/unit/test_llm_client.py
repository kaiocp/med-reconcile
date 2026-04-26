"""Unit tests for the LLM clinical summary adapter."""

from typing import Literal

import pytest

from app.adapters.llm_client import (
    _DISCLAIMER,
    MODEL_IDENTIFIER,
    generate_clinical_summary,
)
from app.models.llm_output import LLMOutputSchema
from app.models.patient_context import MedicationItem, PrescriptionItem
from app.models.response import AllergyConflict, ProcessedInteraction
from app.models.severity import ClinicalSeverity

_NEW_RX = PrescriptionItem(
    drug_name="Warfarin",
    rxnorm_code="11289",
    dosage="5mg PO daily",
    prescriber_id="practitioner-001",
)

_ACTIVE_MEDS = [
    MedicationItem(drug_name="Sertraline", rxnorm_code="36437", dosage="50mg PO daily"),
    MedicationItem(drug_name="Enoxaparin", rxnorm_code="67108", dosage="40mg SC daily"),
]

_INTERACTIONS = [
    ProcessedInteraction(
        medication_a="Warfarin",
        medication_b="Sertraline",
        severity=ClinicalSeverity.HIGH,
        source_severity="major",
        description="SSRI increases warfarin plasma levels via CYP2C9 inhibition.",
    )
]

_ALLERGY_CONFLICTS = [
    AllergyConflict(
        drug_name="Amoxicillin", allergen="Penicillin", conflict_type="cross_reactivity"
    )
]


def _call(
    interactions: list[ProcessedInteraction] | None = None,
    allergy_conflicts: list[AllergyConflict] | None = None,
    allergy_data_status: Literal["available", "unavailable"] = "available",
    pregnancy_status: Literal["active_pregnancy", "not_pregnant", "postpartum"] = "not_pregnant",
) -> LLMOutputSchema | None:
    return generate_clinical_summary(
        patient_id="patient-003",
        new_prescription=_NEW_RX,
        active_medications=_ACTIVE_MEDS,
        interactions=interactions or [],
        allergy_conflicts=allergy_conflicts or [],
        allergy_data_status=allergy_data_status,
        pregnancy_status=pregnancy_status,
    )


def test_returns_llm_output_schema_for_clean_reconciliation() -> None:
    result = _call()
    assert isinstance(result, LLMOutputSchema)


def test_disclaimer_always_present_in_clinical_summary() -> None:
    for result in [
        _call(),
        _call(interactions=_INTERACTIONS),
        _call(allergy_conflicts=_ALLERGY_CONFLICTS),
    ]:
        assert result is not None
        assert _DISCLAIMER in result.clinical_summary


def test_disclaimer_is_the_final_line() -> None:
    result = _call(interactions=_INTERACTIONS)
    assert result is not None
    assert result.clinical_summary.strip().endswith(_DISCLAIMER)


def test_allergy_advisory_appended_when_status_is_available() -> None:
    result = _call(allergy_data_status="available")
    assert result is not None
    assert "updates nightly" in result.clinical_summary


def test_allergy_advisory_appended_when_status_is_unavailable() -> None:
    result = _call(allergy_data_status="unavailable")
    assert result is not None
    assert "could not be performed" in result.clinical_summary


def test_routes_to_interactions_template_when_interactions_present() -> None:
    result = _call(interactions=_INTERACTIONS)
    assert result is not None
    assert "Warfarin" in result.clinical_summary
    assert "Sertraline" in result.clinical_summary
    assert "high severity" in result.clinical_summary


def test_routes_to_allergy_template_when_only_allergy_conflicts() -> None:
    result = _call(allergy_conflicts=_ALLERGY_CONFLICTS)
    assert result is not None
    assert "Amoxicillin" in result.clinical_summary
    assert "Penicillin" in result.clinical_summary


def test_routes_to_clean_template_when_no_interactions_or_conflicts() -> None:
    result = _call()
    assert result is not None
    assert "No drug-drug interactions" in result.clinical_summary


def test_medications_referenced_reflects_drugs_mentioned_in_summary() -> None:
    result = _call(interactions=_INTERACTIONS)
    assert result is not None
    assert "Warfarin" in result.medications_referenced
    assert "Sertraline" in result.medications_referenced


def test_model_identifier_is_present_in_output() -> None:
    result = _call()
    assert result is not None
    assert result.model_identifier == MODEL_IDENTIFIER


def test_contraindicated_uses_teratogenic_language_not_prescriptive() -> None:
    contraindicated = [
        ProcessedInteraction(
            medication_a="Warfarin",
            medication_b="Enoxaparin",
            severity=ClinicalSeverity.CONTRAINDICATED,
            source_severity="major",
            description="Warfarin is teratogenic.",
        )
    ]
    result = _call(interactions=contraindicated, pregnancy_status="active_pregnancy")
    assert result is not None
    assert "teratogenic risk" in result.clinical_summary
    assert "should not be used" not in result.clinical_summary


def test_returns_none_when_generation_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.adapters import llm_client

    monkeypatch.setattr(llm_client, "_CHAT_PROMPT", None)
    result = _call()
    assert result is None
