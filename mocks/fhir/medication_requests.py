"""FHIR R4B MedicationRequest resources representing each patient's currently
active medications. RxCUI codes use the RxNorm system URI and match the codes
used by the DrugBank interaction lookup (Labetalol normalized to 896762)."""

from fhir.resources.R4B.medicationrequest import MedicationRequest

_RXNORM_SYSTEM = "http://www.nlm.nih.gov/research/umls/rxnorm"


def _build(patient_id: str, rxcui: str, display: str, dosage: str) -> MedicationRequest:
    return MedicationRequest(
        status="active",
        intent="order",
        medicationCodeableConcept={
            "coding": [{"system": _RXNORM_SYSTEM, "code": rxcui, "display": display}]
        },
        subject={"reference": f"Patient/{patient_id}"},
        dosageInstruction=[{"text": dosage}],
    )


_MEDS: dict[str, list[MedicationRequest]] = {
    "patient-001": [
        _build("patient-001", "67108", "Enoxaparin", "40mg SC daily"),
        _build("patient-001", "896762", "Labetalol", "200mg PO BID"),
        _build("patient-001", "1191", "Aspirin (low-dose)", "100mg PO daily"),
    ],
    "patient-002": [
        _build("patient-002", "6809", "Metformin", "500mg PO BID"),
        _build("patient-002", "72965", "Letrozole", "5mg PO daily"),
        _build("patient-002", "8727", "Progesterone", "200mg vaginal daily"),
    ],
    "patient-003": [
        _build("patient-003", "36437", "Sertraline", "50mg PO daily"),
        _build("patient-003", "67108", "Enoxaparin", "40mg SC daily"),
    ],
}


def get_active_medications(patient_id: str) -> list[MedicationRequest]:
    return _MEDS.get(patient_id, [])
