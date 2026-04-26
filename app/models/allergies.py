"""Typed contracts for patient allergy data.

The allergy adapter parses raw CSV rows into ``AllergyRecord`` instances
at the adapter boundary. ``AllergyDataStatus`` signals whether the
underlying source was reachable — it is paired with the records list so
the service layer (and ultimately the API response) can communicate
"screening could not be performed" distinctly from "no allergies on
record."
"""

from typing import Literal

from pydantic import BaseModel

AllergyDataStatus = Literal["available", "unavailable"]


class AllergyRecord(BaseModel):
    """One patient allergy record as exported from the allergy source."""

    patient_id: str
    allergen: str
    reaction_type: str
    severity: str
    documented_date: str
