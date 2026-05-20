"""FastAPI application entry point for the medication reconciliation service."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import _sanitize_validation_error, router

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

app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    patient_id: str | None = None
    try:
        body = await request.json()
        patient_id = body.get("patient_id")
    except Exception:
        pass
    return _sanitize_validation_error(exc, patient_id)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe for container orchestration and CI."""
    return {"status": "ok"}
