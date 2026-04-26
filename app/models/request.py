"""API request schemas with input validation at the service boundary."""

from pydantic import BaseModel, Field


class NewPrescription(BaseModel):
    drug_name: str = Field(..., min_length=1)
    rxnorm_code: str = Field(..., pattern=r"^\d+$")
    dosage: str = Field(..., min_length=1)
    prescriber_id: str = Field(..., min_length=1)


class ReconciliationRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    new_prescription: NewPrescription
