"""Step definitions for safe_failure.feature."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.adapters import fhir_client
from tests.step_defs.conftest import prescription_payload

scenarios("../features/safe_failure.feature")


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("the FHIR clinical records system is unreachable")
def given_fhir_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise RuntimeError("FHIR connection refused")

    monkeypatch.setattr(fhir_client, "get_patient", _raise)


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when(
    parsers.parse('a reconciliation is requested for patient "{patient_id}"'),
    target_fixture="response",
)
def when_reconciliation_requested(client: TestClient, patient_id: str):
    return client.post(
        "/api/v1/reconciliation",
        json=prescription_payload("Warfarin", patient_id),
    )


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then("the service responds with a structured error")
def then_structured_error(response) -> None:
    body = response.json()
    assert response.status_code == 503, body
    # FastAPI wraps HTTPException detail in {"detail": {...}}
    detail = body["detail"]
    assert detail["status"] == "error"
    assert "error_code" in detail
    assert "message" in detail
    assert "timestamp" in detail


@then("the error indicates that patient data could not be retrieved")
def then_fhir_unavailable_error_code(response) -> None:
    body = response.json()
    assert body["detail"]["error_code"] == "fhir_unavailable"


@then("no partial reconciliation result is returned")
def then_no_partial_result(response) -> None:
    body = response.json()
    assert "interactions" not in body
    assert "active_medications" not in body
    assert "clinical_summary" not in body
