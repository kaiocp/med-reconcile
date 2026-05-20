"""DrugBank drug-drug interaction adapter — wraps the DrugBank-style mock.

In production, this module would replace the ``mocks.drugbank`` import
with HTTP calls to the real interaction service and parse the response
JSON the same way it parses the mock dict — through Pydantic. The
lookup is order-independent and returns ``None`` for unknown pairs
(mirroring production behavior: absence of a record means no known
interaction in the reference data, not that the pair is confirmed safe).
"""

from app.models.drug_interactions import InteractionRecord
from mocks.drugbank import interactions as _interactions


def check_interaction(rxnorm_code_a: str, rxnorm_code_b: str) -> InteractionRecord | None:
    raw = _interactions.check_interaction(rxnorm_code_a, rxnorm_code_b)
    if raw is None:
        return None
    return InteractionRecord.model_validate(raw)
