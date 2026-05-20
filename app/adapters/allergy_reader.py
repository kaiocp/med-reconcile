"""Patient allergy adapter — wraps the CSV-backed mock.

The CSV is re-read on every call per the CTO's directive; the data lives
in a separate system and is exported nightly. The risks of this design
(stale data window, IO cost per request, malformed CSV producing silent
gaps) are documented in RISKS.md.

``get_patient_allergies_safe`` is the service-facing entry point. It
guarantees the reconciliation never crashes on a malformed allergy
source — instead it signals explicitly that allergy screening could not
be performed, so the response can carry that fact to the physician
rather than treat the patient as if they had no allergies.
"""

from app.models.allergies import AllergyDataStatus, AllergyRecord
from mocks.allergies import allergy_reader as _allergy_reader


def get_patient_allergies(patient_id: str) -> list[AllergyRecord]:
    raw_records = _allergy_reader.get_patient_allergies(patient_id)
    return [AllergyRecord.model_validate(record) for record in raw_records]


def get_patient_allergies_safe(
    patient_id: str,
) -> tuple[list[AllergyRecord], AllergyDataStatus]:
    try:
        return get_patient_allergies(patient_id), "available"
    except Exception:
        return [], "unavailable"
