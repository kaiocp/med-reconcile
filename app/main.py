"""FastAPI application entry point for the medication reconciliation service."""

from fastapi import FastAPI

app = FastAPI(
    title="Medication Reconciliation Service",
    description=(
        "Backend integration service that compares a patient's active medications "
        "against a new prescription, flags potential interactions, and produces a "
        "plain-language clinical summary for physician review. Sits between the "
        "EHR's FHIR API and a drug interaction database."
    ),
    version="0.1.0",
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe for container orchestration and CI."""
    return {"status": "ok"}
