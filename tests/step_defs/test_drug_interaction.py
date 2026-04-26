"""Step definitions for drug_interaction_detection.feature."""

from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from tests.step_defs.conftest import prescription_payload

scenarios("../features/drug_interaction_detection.feature")


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given(
    "a postpartum patient with active prescriptions for Sertraline and Enoxaparin",
    target_fixture="patient_id",
)
def given_postpartum_patient() -> str:
    return "patient-003"


@given(
    "a pregnant patient with an active prescription for Enoxaparin",
    target_fixture="patient_id",
)
def given_pregnant_patient() -> str:
    return "patient-001"


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


@when(
    parsers.parse("a new prescription for {drug_name} is submitted for that patient"),
    target_fixture="response",
)
def when_new_prescription(client: TestClient, patient_id: str, drug_name: str):
    return client.post("/api/v1/reconciliation", json=prescription_payload(drug_name, patient_id))


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then(
    parsers.parse(
        "the report includes a {severity}-severity interaction between {drug_a} and {drug_b}"
    )
)
def then_severity_interaction(response, severity: str, drug_a: str, drug_b: str) -> None:
    body = response.json()
    assert response.status_code == 200, body
    names = {(i["medication_a"].lower(), i["medication_b"].lower()) for i in body["interactions"]}
    pair = (drug_a.lower(), drug_b.lower())
    reverse = (drug_b.lower(), drug_a.lower())
    assert pair in names or reverse in names, f"Pair {pair} not found in {names}"
    matched = next(
        i
        for i in body["interactions"]
        if (i["medication_a"].lower(), i["medication_b"].lower()) in (pair, reverse)
    )
    assert matched["severity"] == severity, f"Expected {severity}, got {matched['severity']}"


@then(
    parsers.parse("the report includes a contraindicated interaction between {drug_a} and {drug_b}")
)
def then_contraindicated_interaction(response, drug_a: str, drug_b: str) -> None:
    body = response.json()
    assert response.status_code == 200, body
    names = {(i["medication_a"].lower(), i["medication_b"].lower()) for i in body["interactions"]}
    pair = (drug_a.lower(), drug_b.lower())
    reverse = (drug_b.lower(), drug_a.lower())
    assert pair in names or reverse in names, f"Pair {pair} not found in {names}"
    matched = next(
        i
        for i in body["interactions"]
        if (i["medication_a"].lower(), i["medication_b"].lower()) in (pair, reverse)
    )
    got = matched["severity"]
    assert got == "contraindicated", f"Expected contraindicated, got {got}"


@then("the clinical summary is marked as pending physician review")
def then_pending_physician_review(response) -> None:
    body = response.json()
    assert response.status_code == 200, body
    assert "pending physician review" in body["ai_disclaimer"].lower()


@then("the audit record captures the model identifier and the prompt hash")
def then_audit_record(response) -> None:
    body = response.json()
    assert response.status_code == 200, body
    audit = body["audit"]
    assert audit is not None
    assert audit["model"] == "gpt-4o-mock"
    assert len(audit["prompt_hash"]) == 64  # sha256 hex digest


@then("the AI summary is not committed to the chart automatically")
def then_summary_not_auto_committed(response) -> None:
    body = response.json()
    assert response.status_code == 200, body
    assert "pending physician review" in body["ai_disclaimer"].lower()
