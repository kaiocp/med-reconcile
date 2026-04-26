"""FHIR R4B Patient resources for the 3 mock patients plus a separate
pregnancy-status lookup.

Pregnancy status is intentionally kept out of the Patient resource — the
FHIR R4B Patient model has no native pregnancy field, and modeling it via
Observation/extension would add boilerplate disproportionate to a 3-patient
mock. The reconciliation service consumes pregnancy status via
``get_pregnancy_status`` instead.
"""

from fhir.resources.R4B.patient import Patient

_PATIENTS: dict[str, Patient] = {
    "patient-001": Patient(
        id="patient-001",
        name=[{"use": "official", "family": "Santos", "given": ["Maria"]}],
        gender="female",
        birthDate="1992-03-15",
    ),
    "patient-002": Patient(
        id="patient-002",
        name=[{"use": "official", "family": "Oliveira", "given": ["Julia"]}],
        gender="female",
        birthDate="1988-11-22",
    ),
    "patient-003": Patient(
        id="patient-003",
        name=[{"use": "official", "family": "Ferreira", "given": ["Camila"]}],
        gender="female",
        birthDate="1995-07-08",
    ),
}

# In production, this would be sourced from a FHIR Observation resource
# (LOINC 82810-3 "Pregnancy status") queried alongside the Patient.
# Adding a third FHIR resource type mock for a single status value would
# be overengineering for 3 patients.
PREGNANCY_STATUS: dict[str, str] = {
    "patient-001": "active_pregnancy",
    "patient-002": "not_pregnant",
    "patient-003": "postpartum",
}


def get_patient(patient_id: str) -> Patient | None:
    return _PATIENTS.get(patient_id)


def get_pregnancy_status(patient_id: str) -> str | None:
    return PREGNANCY_STATUS.get(patient_id)
