"""Patient clinical context types.

These are the typed shapes the service layer receives from the FHIR
adapter (or, in production, from clinical observation queries). Keeping
them as a closed ``Literal`` set means downstream code that reasons
about pregnancy status — most notably the contraindication overlay —
gets compile-time coverage on every branch.
"""

from typing import Literal

from pydantic import BaseModel

PregnancyStatus = Literal["active_pregnancy", "not_pregnant", "postpartum"]


class MedicationItem(BaseModel):
    """A medication on a patient's active list."""

    drug_name: str
    rxnorm_code: str
    dosage: str


class PrescriptionItem(MedicationItem):
    """A new prescription being evaluated — extends MedicationItem with prescriber context."""

    prescriber_id: str
