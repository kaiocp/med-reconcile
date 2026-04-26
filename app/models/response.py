"""API response schemas and embedded result models."""

from typing import Literal

from pydantic import BaseModel

from app.models.allergies import AllergyDataStatus
from app.models.patient_context import MedicationItem
from app.models.request import NewPrescription
from app.models.severity import ClinicalSeverity


class AllergyConflict(BaseModel):
    """A single allergy conflict detected between a new prescription and patient records."""

    drug_name: str  # The new prescription drug that conflicts
    allergen: str  # The documented allergen it conflicts with
    conflict_type: Literal["direct", "cross_reactivity"]


class ProcessedInteraction(BaseModel):
    """A drug-drug interaction after severity mapping and pregnancy overlay have been applied."""

    medication_a: str
    medication_b: str
    severity: ClinicalSeverity
    source_severity: str
    description: str


class ValidationFlag(BaseModel):
    """A flag raised by the deterministic LLM output validation layer."""

    type: str  # "unrecognized_medication" | "severity_mismatch" | "missing_disclaimer"
    detail: str  # Clinician-appropriate explanation
    flag_severity: str  # "warning" | "critical"


class InteractionResult(BaseModel):
    """A fully-resolved drug-drug interaction ready for the API response."""

    medication_a: str
    medication_a_rxnorm: str
    medication_b: str
    medication_b_rxnorm: str
    severity: ClinicalSeverity
    source_severity: str
    source: str  # "drugbank"
    description: str


class AuditInfo(BaseModel):
    """Audit record attached to every LLM-generated clinical summary."""

    model: str
    prompt_hash: str
    temperature: int
    validation_status: Literal["passed", "flagged"]
    generated_at: str  # ISO-8601


class ReconciliationResponse(BaseModel):
    """Full reconciliation result returned by the pipeline."""

    reconciliation_id: str
    patient_id: str
    timestamp: str
    new_prescription: NewPrescription
    active_medications: list[MedicationItem]
    pairs_checked: int
    interactions: list[InteractionResult]
    allergy_conflicts: list[AllergyConflict]
    allergy_data_status: AllergyDataStatus
    allergy_data_reason: str | None
    clinical_summary: str | None
    summary_status: Literal["generated", "unavailable"]
    summary_status_reason: str | None
    validation_flags: list[ValidationFlag]
    ai_disclaimer: str
    audit: AuditInfo | None


class ErrorResponse(BaseModel):
    """Structured error envelope returned on hard failures."""

    status: str  # always "error"
    error_code: str
    message: str
    patient_id: str | None
    detail: str | None
    timestamp: str
