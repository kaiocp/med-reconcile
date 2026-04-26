"""Patient clinical context types.

These are the typed shapes the service layer receives from the FHIR
adapter (or, in production, from clinical observation queries). Keeping
them as a closed ``Literal`` set means downstream code that reasons
about pregnancy status — most notably the contraindication overlay —
gets compile-time coverage on every branch.
"""

from typing import Literal

PregnancyStatus = Literal["active_pregnancy", "not_pregnant", "postpartum"]
