"""Adapter-layer contract tests.

These tests pin the typed function signatures the service layer depends
on — both the happy path (known IDs, valid records) and the negative
shapes that drove design decisions (unknown patient → ``None``/empty,
malformed source → degraded status).
"""

import pytest
from fhir.resources.R4B.medicationrequest import MedicationRequest
from fhir.resources.R4B.patient import Patient

from app.adapters import allergy_reader, drugbank_client, fhir_client
from app.models.allergies import AllergyRecord
from app.models.drug_interactions import InteractionRecord

# ---- FHIR adapter ----------------------------------------------------------


def test_get_patient_returns_patient_instance_for_known_id() -> None:
    patient = fhir_client.get_patient("patient-001")
    assert isinstance(patient, Patient)


def test_get_patient_returns_none_for_unknown_id() -> None:
    assert fhir_client.get_patient("patient-999") is None


def test_get_pregnancy_status_returns_active_pregnancy_for_patient_001() -> None:
    assert fhir_client.get_pregnancy_status("patient-001") == "active_pregnancy"


def test_get_pregnancy_status_returns_postpartum_for_patient_003() -> None:
    assert fhir_client.get_pregnancy_status("patient-003") == "postpartum"


def test_get_pregnancy_status_returns_none_for_unknown_id() -> None:
    assert fhir_client.get_pregnancy_status("patient-999") is None


def test_get_pregnancy_status_raises_on_unexpected_source_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "mocks.fhir.patients.get_pregnancy_status",
        lambda _patient_id: "trimester_1",
    )

    with pytest.raises(ValueError, match="Unexpected pregnancy status"):
        fhir_client.get_pregnancy_status("patient-001")


def test_get_active_medications_returns_three_items_for_patient_001() -> None:
    meds = fhir_client.get_active_medications("patient-001")
    assert len(meds) == 3
    assert all(isinstance(m, MedicationRequest) for m in meds)


def test_get_active_medications_returns_three_items_for_patient_002() -> None:
    assert len(fhir_client.get_active_medications("patient-002")) == 3


def test_get_active_medications_returns_two_items_for_patient_003() -> None:
    assert len(fhir_client.get_active_medications("patient-003")) == 2


def test_get_active_medications_returns_empty_list_for_unknown_id() -> None:
    assert fhir_client.get_active_medications("patient-999") == []


# ---- DrugBank adapter ------------------------------------------------------


def test_check_interaction_returns_typed_record_for_warfarin_sertraline() -> None:
    result = drugbank_client.check_interaction("11289", "36437")

    assert isinstance(result, InteractionRecord)
    assert result.drugbank_severity == "major"
    assert result.contraindication is False
    assert "SSRI" in result.description
    assert {result.drug_a.rxnorm_code, result.drug_b.rxnorm_code} == {"11289", "36437"}


def test_check_interaction_is_order_independent() -> None:
    a_then_b = drugbank_client.check_interaction("11289", "36437")
    b_then_a = drugbank_client.check_interaction("36437", "11289")

    assert a_then_b == b_then_a


def test_check_interaction_returns_none_for_unknown_pair() -> None:
    assert drugbank_client.check_interaction("8727", "72965") is None


# ---- Allergy adapter -------------------------------------------------------


def test_get_patient_allergies_returns_typed_record_for_patient_001() -> None:
    allergies = allergy_reader.get_patient_allergies("patient-001")

    assert len(allergies) == 1
    assert isinstance(allergies[0], AllergyRecord)
    assert allergies[0].allergen == "Penicillin"


def test_get_patient_allergies_returns_empty_list_for_patient_with_no_records() -> None:
    assert allergy_reader.get_patient_allergies("patient-003") == []


def test_get_patient_allergies_safe_returns_available_status_on_success() -> None:
    allergies, status = allergy_reader.get_patient_allergies_safe("patient-001")

    assert status == "available"
    assert len(allergies) == 1
    assert isinstance(allergies[0], AllergyRecord)


@pytest.mark.parametrize(
    "raised_exception",
    [
        OSError("simulated I/O failure"),
        ValueError("simulated parsing failure"),
        KeyError("patient_id"),
    ],
)
def test_get_patient_allergies_safe_returns_unavailable_when_source_raises(
    monkeypatch: pytest.MonkeyPatch, raised_exception: Exception
) -> None:
    def raise_failure(_patient_id: str) -> list[dict[str, str]]:
        raise raised_exception

    monkeypatch.setattr(
        "mocks.allergies.allergy_reader.get_patient_allergies",
        raise_failure,
    )

    allergies, status = allergy_reader.get_patient_allergies_safe("patient-001")

    assert status == "unavailable"
    assert allergies == []
