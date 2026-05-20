"""Typed contracts for drug-drug interaction data.

The DrugBank adapter parses raw mock (eventually: API) responses into
these Pydantic models at the adapter boundary, so the service layer
operates on typed shapes rather than ``dict[str, Any]``. Severity is a
closed ``Literal`` set matching DrugBank's native categories — the
deterministic clinical-severity mapping consumes this in a later step.
"""

from typing import Literal

from pydantic import BaseModel

DrugbankSeverity = Literal["minor", "moderate", "major"]


class DrugRef(BaseModel):
    """Reference to a drug by RxNorm code + display name."""

    rxnorm_code: str
    name: str


class InteractionRecord(BaseModel):
    """A single drug-drug interaction as returned by the DrugBank source."""

    drug_a: DrugRef
    drug_b: DrugRef
    drugbank_severity: DrugbankSeverity
    contraindication: bool
    description: str
    evidence_level: int
