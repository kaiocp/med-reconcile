"""API response schemas and embedded result models.

Defines the Pydantic models that appear in the reconciliation response. The
full ``ReconciliationResponse`` is assembled here once the pipeline commit
wires the orchestrator — for now only ``AllergyConflict`` is needed by the
allergy checker service.
"""

from typing import Literal

from pydantic import BaseModel


class AllergyConflict(BaseModel):
    """A single allergy conflict detected between a new prescription and patient records."""

    drug_name: str  # The new prescription drug that conflicts
    allergen: str  # The documented allergen it conflicts with
    conflict_type: Literal["direct", "cross_reactivity"]


class ProcessedInteraction(BaseModel):
    """A drug-drug interaction after severity mapping and pregnancy overlay have been applied."""

    medication_a: str
    medication_b: str
    severity: str  # ClinicalSeverity value — kept as str to avoid models → services import
    source_severity: str
    description: str
