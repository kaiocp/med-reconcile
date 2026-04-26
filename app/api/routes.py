"""Reconciliation API routes — request routing and error shaping only."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.request import ReconciliationRequest
from app.models.response import ErrorResponse, ReconciliationResponse
from app.services.reconciliation import FHIRUnavailableError, PatientNotFoundError, reconcile
from app.store import audit_store

router = APIRouter(prefix="/api/v1", tags=["reconciliation"])

_MSG_PATIENT_NOT_FOUND = (
    "The patient identifier '{patient_id}' was not found in the records system."
)
_MSG_FHIR_UNAVAILABLE = (
    "The clinical records system is currently unavailable. " "Please retry the reconciliation."
)
_MSG_RECONCILIATION_NOT_FOUND = "No reconciliation record was found for the provided identifier."

_404_EXAMPLE = {
    "description": "Patient not found",
    "content": {
        "application/json": {
            "example": {
                "status": "error",
                "error_code": "patient_not_found",
                "message": _MSG_PATIENT_NOT_FOUND.format(patient_id="patient-999"),
                "patient_id": "patient-999",
                "detail": None,
                "timestamp": "2026-04-26T12:00:00+00:00",
            }
        }
    },
}

_422_EXAMPLE = {
    "description": "Invalid request data",
    "content": {
        "application/json": {
            "example": {
                "status": "error",
                "error_code": "invalid_prescription_data",
                "message": (
                    "The medication code 'abc123' is not valid. " "RxNorm codes must be numeric."
                ),
                "patient_id": None,
                "detail": None,
                "timestamp": "2026-04-26T12:00:00+00:00",
            }
        }
    },
}

_503_EXAMPLE = {
    "description": "FHIR system unavailable",
    "content": {
        "application/json": {
            "example": {
                "status": "error",
                "error_code": "fhir_unavailable",
                "message": _MSG_FHIR_UNAVAILABLE,
                "patient_id": "patient-001",
                "detail": None,
                "timestamp": "2026-04-26T12:00:00+00:00",
            }
        }
    },
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    patient_id: str | None = None,
    detail: str | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            status="error",
            error_code=error_code,
            message=message,
            patient_id=patient_id,
            detail=detail,
            timestamp=_now(),
        ).model_dump(),
    )


def _sanitize_validation_error(exc: RequestValidationError, patient_id: str | None) -> JSONResponse:
    """Translate raw Pydantic validation errors into clinician-appropriate messages."""
    message = (
        "One or more fields in the request are invalid. " "Please check the input and resubmit."
    )

    for error in exc.errors():
        error_type = error.get("type", "")
        loc = error.get("loc", ())
        field = loc[-1] if loc else ""

        if error_type == "string_pattern_mismatch" and field == "rxnorm_code":
            input_val = error.get("input", "")
            message = (
                f"The medication code '{input_val}' is not valid. " "RxNorm codes must be numeric."
            )
            break
        if error_type == "string_too_short" and field == "patient_id":
            message = "Patient identifier must not be empty."
            break

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            status="error",
            error_code="invalid_prescription_data",
            message=message,
            patient_id=patient_id,
            detail=None,
            timestamp=_now(),
        ).model_dump(),
    )


@router.post(
    "/reconciliation",
    response_model=ReconciliationResponse,
    status_code=200,
    responses={
        404: _404_EXAMPLE,
        422: _422_EXAMPLE,
        503: _503_EXAMPLE,
    },
)
def create_reconciliation(request: ReconciliationRequest) -> ReconciliationResponse:
    """Run a medication reconciliation and persist the result for audit retrieval."""
    try:
        response = reconcile(request)
    except PatientNotFoundError as exc:
        raise _error_response(
            404,
            "patient_not_found",
            _MSG_PATIENT_NOT_FOUND.format(patient_id=request.patient_id),
            patient_id=request.patient_id,
            detail=str(exc),
        ) from exc
    except FHIRUnavailableError as exc:
        raise _error_response(
            503,
            "fhir_unavailable",
            _MSG_FHIR_UNAVAILABLE,
            patient_id=request.patient_id,
            detail=str(exc),
        ) from exc

    audit_store.save(response)
    return response


@router.get(
    "/reconciliation/{reconciliation_id}",
    response_model=ReconciliationResponse,
    status_code=200,
    responses={
        404: {
            "description": "Reconciliation record not found",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "error_code": "reconciliation_not_found",
                        "message": _MSG_RECONCILIATION_NOT_FOUND,
                        "patient_id": None,
                        "detail": None,
                        "timestamp": "2026-04-26T12:00:00+00:00",
                    }
                }
            },
        }
    },
)
def get_reconciliation(reconciliation_id: str) -> ReconciliationResponse:
    """Retrieve a previously stored reconciliation result by ID."""
    result = audit_store.get(reconciliation_id)
    if result is None:
        raise _error_response(404, "reconciliation_not_found", _MSG_RECONCILIATION_NOT_FOUND)
    return result
