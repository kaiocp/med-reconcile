"""API response schemas and embedded result models.

Defines the Pydantic models that appear in the reconciliation response. The
full ``ReconciliationResponse`` is assembled here once the pipeline commit
wires the orchestrator — for now only ``AllergyConflict`` is needed by the
allergy checker service.
"""

from typing import Literal

from pydantic import BaseModel

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
