"""Integration tests for the POST /api/v1/reconciliation and GET endpoints.

Uses FastAPI's TestClient against the real app with mock adapters (no network).
All tests clear the audit store before/after to ensure isolation.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.severity import ClinicalSeverity
from app.store import audit_store

_AI_DISCLAIMER = "This summary was generated with AI assistance and is pending physician review."

_BASE_PRESCRIPTION = {
    "dosage": "5mg PO daily",
    "prescriber_id": "practitioner-001",
}


@pytest.fixture(autouse=True)
def _clear_store() -> Iterator[None]:
    audit_store.clear()
    yield
    audit_store.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _post(client: TestClient, patient_id: str, drug_name: str, rxnorm_code: str):  # noqa: ANN201
    return client.post(
        "/api/v1/reconciliation",
        json={
            "patient_id": patient_id,
            "new_prescription": {
                "drug_name": drug_name,
                "rxnorm_code": rxnorm_code,
                **_BASE_PRESCRIPTION,
            },
        },
    )


def _assert_common_fields(body: dict[str, object]) -> None:
    assert body["ai_disclaimer"] == _AI_DISCLAIMER
    if body.get("summary_status") == "generated":
        summary = body["clinical_summary"]
        assert isinstance(summary, str)
        assert "pending physician review" in summary
        audit = body["audit"]
        assert isinstance(audit, dict)
        assert audit["model"] == "gpt-4o-mock"
        prompt_hash = audit["prompt_hash"]
        assert isinstance(prompt_hash, str) and len(prompt_hash) == 64
        assert audit["temperature"] == 0.0
    severity_values = {s.value for s in ClinicalSeverity}
    interactions = body.get("interactions", [])
    assert isinstance(interactions, list)
    for interaction in interactions:
        assert isinstance(interaction, dict)
        assert interaction["severity"] in severity_values


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_patient_001_nifedipine_one_moderate_interaction(client: TestClient) -> None:
    """patient-001 (pregnant) + Nifedipine → 1 moderate interaction with Labetalol."""
    resp = _post(client, "patient-001", "Nifedipine", "7417")
    assert resp.status_code == 200
    body = resp.json()

    assert body["pairs_checked"] == 3
    assert len(body["interactions"]) == 1

    interaction = body["interactions"][0]
    drug_names = {interaction["medication_a"].lower(), interaction["medication_b"].lower()}
    assert "nifedipine" in drug_names
    assert "labetalol" in drug_names
    assert interaction["severity"] == ClinicalSeverity.MODERATE.value

    _assert_common_fields(body)


def test_patient_001_amoxicillin_penicillin_allergy_caught(client: TestClient) -> None:
    """patient-001 (Penicillin allergy) + Amoxicillin → cross-reactivity conflict."""
    resp = _post(client, "patient-001", "Amoxicillin", "723")
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["allergy_conflicts"]) >= 1
    conflict = next(c for c in body["allergy_conflicts"] if c["allergen"] == "Penicillin")
    assert conflict["conflict_type"] == "cross_reactivity"

    _assert_common_fields(body)


def test_patient_002_sertraline_clean_no_sulfonamide_false_positive(client: TestClient) -> None:
    """patient-002 (Sulfonamides allergy) + Sertraline → no interactions or allergy conflicts."""
    resp = _post(client, "patient-002", "Sertraline", "36437")
    assert resp.status_code == 200
    body = resp.json()

    assert body["interactions"] == []
    assert body["allergy_conflicts"] == []
    assert body["summary_status"] == "generated"
    assert body["audit"]["validation_status"] == "passed"

    _assert_common_fields(body)


def test_patient_003_warfarin_two_high_severity_interactions(client: TestClient) -> None:
    """patient-003 (postpartum) + Warfarin → 2 high-severity interactions; no contraindication."""
    resp = _post(client, "patient-003", "Warfarin", "11289")
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["interactions"]) == 2
    severities = {i["severity"] for i in body["interactions"]}
    assert severities == {"high"}

    _assert_common_fields(body)


def test_patient_999_not_found_returns_404(client: TestClient) -> None:
    """Unknown patient → 404 with clinician-appropriate error message."""
    resp = _post(client, "patient-999", "Warfarin", "11289")
    assert resp.status_code == 404
    body = resp.json()["detail"]
    assert body["error_code"] == "patient_not_found"
    assert "patient-999" in body["message"]
    assert body["status"] == "error"


def test_invalid_rxnorm_code_returns_422(client: TestClient) -> None:
    """Non-numeric RxNorm code → 422 with sanitized, clinician-appropriate message."""
    resp = _post(client, "patient-001", "Warfarin", "abc123")
    assert resp.status_code == 422
    body = resp.json()
    assert body["error_code"] == "invalid_prescription_data"
    assert "abc123" in body["message"]
    assert "RxNorm" in body["message"]
    assert "ctx" not in body


def test_empty_patient_id_returns_422(client: TestClient) -> None:
    """Empty patient_id → 422 with sanitized message (no Pydantic internals)."""
    resp = _post(client, "", "Warfarin", "11289")
    assert resp.status_code == 422
    body = resp.json()
    assert body["error_code"] == "invalid_prescription_data"
    assert "ctx" not in body


def test_get_reconciliation_by_id_returns_stored_result(client: TestClient) -> None:
    """POST then GET by reconciliation_id → identical full body."""
    post_resp = _post(client, "patient-003", "Warfarin", "11289")
    assert post_resp.status_code == 200
    posted = post_resp.json()
    rec_id = posted["reconciliation_id"]

    get_resp = client.get(f"/api/v1/reconciliation/{rec_id}")
    assert get_resp.status_code == 200
    assert get_resp.json() == posted


def test_get_nonexistent_reconciliation_returns_404(client: TestClient) -> None:
    """GET unknown reconciliation_id → 404 with reconciliation_not_found error_code."""
    resp = client.get("/api/v1/reconciliation/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()["detail"]
    assert body["error_code"] == "reconciliation_not_found"
    assert body["status"] == "error"
