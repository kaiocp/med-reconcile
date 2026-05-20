"""Step definitions for llm_output_validation.feature."""

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from app.adapters import llm_client
from app.models.llm_output import LLMOutputSchema
from tests.step_defs.conftest import prescription_payload

scenarios("../features/llm_output_validation.feature")

_DISCLAIMER = "This summary was generated with AI assistance and is pending physician review."


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given(
    "a fertility patient whose active medications are Metformin, Letrozole, and Progesterone",
    target_fixture="patient_id",
)
def given_fertility_patient() -> str:
    return "patient-002"


@given("allergy data for that patient is available")
def given_allergy_data_available() -> None:
    pass


@given(
    "a new prescription for Sertraline is submitted for that patient",
    target_fixture="prescription_setup",
)
def given_sertraline_prescription() -> dict[str, object]:
    return prescription_payload("Sertraline", "patient-002")


@given("the language model produces a clinical summary that also references Clopidogrel")
def given_llm_references_clopidogrel(monkeypatch: pytest.MonkeyPatch) -> None:
    def _hallucinated_summary(**kwargs: object) -> LLMOutputSchema:
        return LLMOutputSchema(
            clinical_summary=("Sertraline review: Clopidogrel interaction noted. " + _DISCLAIMER),
            medications_referenced=["Sertraline", "Clopidogrel"],
            disclaimer=_DISCLAIMER,
            model_identifier="gpt-4o-mock",
        )

    monkeypatch.setattr(llm_client, "generate_clinical_summary", _hallucinated_summary)


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when("a new prescription for Sertraline is submitted", target_fixture="response")
def when_sertraline_submitted(client: TestClient, patient_id: str):
    payload = prescription_payload("Sertraline", patient_id)
    return client.post("/api/v1/reconciliation", json=payload)


@when("the reconciliation pipeline runs", target_fixture="response")
def when_pipeline_runs(client: TestClient, prescription_setup: dict[str, object]):
    return client.post("/api/v1/reconciliation", json=prescription_setup)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then("the clinical summary includes the AI-generated physician review disclaimer")
def then_disclaimer_present(response) -> None:
    body = response.json()
    assert response.status_code == 200, body
    assert body["clinical_summary"] is not None
    assert "pending physician review" in body["clinical_summary"].lower()


@then("the clinical summary includes an allergy data freshness advisory")
def then_freshness_advisory(response) -> None:
    body = response.json()
    assert response.status_code == 200, body
    assert body["clinical_summary"] is not None
    assert "updates nightly" in body["clinical_summary"]


@then('the response includes a validation flag of type "unrecognized_medication"')
def then_unrecognized_medication_flag(response) -> None:
    body = response.json()
    assert response.status_code == 200, body
    flag_types = [f["type"] for f in body["validation_flags"]]
    assert "unrecognized_medication" in flag_types, f"Flags: {flag_types}"


@then("the flag detail names Clopidogrel as the unrecognized medication")
def then_flag_names_clopidogrel(response) -> None:
    body = response.json()
    flags = [f for f in body["validation_flags"] if f["type"] == "unrecognized_medication"]
    assert any("Clopidogrel" in f["detail"] for f in flags), f"Flags: {flags}"


@then("the audit record marks the validation status as flagged")
def then_audit_flagged(response) -> None:
    body = response.json()
    assert body["audit"] is not None
    assert body["audit"]["validation_status"] == "flagged"
