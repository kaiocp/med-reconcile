"""FHIR API adapter — wraps the FHIR R4B mock for this engagement.

In production, this module would replace the ``mocks.fhir`` imports with
HTTP calls to the client's FHIR R4 server. The function signatures are
the contract the service layer depends on; nothing in ``app/services/``
needs to know whether the data came from a fixture or a live API.

``get_pregnancy_status`` validates the source value against the closed
``PregnancyStatus`` Literal set and raises ``ValueError`` on anything
else — pregnancy status drives the contraindication overlay, so a value
the system doesn't recognize must surface as a loud failure rather than
silently fall through to a postpartum or not-pregnant default.
"""

from typing import cast

from fhir.resources.R4B.medicationrequest import MedicationRequest
from fhir.resources.R4B.patient import Patient

from app.models.patient_context import MedicationItem, PregnancyStatus
from mocks.fhir import medication_requests as _medication_requests
from mocks.fhir import patients as _patients

_VALID_PREGNANCY_STATUSES: frozenset[str] = frozenset(
    {"active_pregnancy", "not_pregnant", "postpartum"}
)


def get_patient(patient_id: str) -> Patient | None:
    return _patients.get_patient(patient_id)


def get_pregnancy_status(patient_id: str) -> PregnancyStatus | None:
    value = _patients.get_pregnancy_status(patient_id)
    if value is None:
        return None
    if value not in _VALID_PREGNANCY_STATUSES:
        raise ValueError(
            f"Unexpected pregnancy status from FHIR source: {value!r}. "
            f"Expected one of {sorted(_VALID_PREGNANCY_STATUSES)}."
        )
    return cast(PregnancyStatus, value)


def get_active_medications(patient_id: str) -> list[MedicationRequest]:
    return _medication_requests.get_active_medications(patient_id)


def _to_medication_item(med: MedicationRequest) -> MedicationItem:
    # fhir.resources.R4B field names are camelCase matching the FHIR JSON spec
    coding = med.medicationCodeableConcept.coding[0]  # type: ignore[union-attr,index]
    dosage_instructions = med.dosageInstruction
    dosage_text = dosage_instructions[0].text if dosage_instructions else ""
    return MedicationItem(
        drug_name=str(coding.display or coding.code),
        rxnorm_code=str(coding.code),
        dosage=str(dosage_text) if dosage_text else "",
    )


def get_active_medications_as_items(patient_id: str) -> list[MedicationItem]:
    return [_to_medication_item(m) for m in get_active_medications(patient_id)]
