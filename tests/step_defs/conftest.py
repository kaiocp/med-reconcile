"""Shared fixtures for pytest-bdd step definitions."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import audit_store


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_audit_store() -> Iterator[None]:
    audit_store.clear()
    yield
    audit_store.clear()


_PRESCRIPTIONS: dict[str, dict[str, str]] = {
    "Warfarin": {
        "drug_name": "Warfarin",
        "rxnorm_code": "11289",
        "dosage": "5mg PO daily",
        "prescriber_id": "practitioner-001",
    },
    "Sertraline": {
        "drug_name": "Sertraline",
        "rxnorm_code": "36437",
        "dosage": "50mg PO daily",
        "prescriber_id": "practitioner-001",
    },
    "Enoxaparin": {
        "drug_name": "Enoxaparin",
        "rxnorm_code": "67108",
        "dosage": "40mg SC daily",
        "prescriber_id": "practitioner-001",
    },
}


def prescription_payload(drug_name: str, patient_id: str) -> dict[str, object]:
    return {
        "patient_id": patient_id,
        "new_prescription": _PRESCRIPTIONS[drug_name],
    }
