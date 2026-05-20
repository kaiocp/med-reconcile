"""In-memory audit store for reconciliation results.

Append-only dict keyed by reconciliation_id. Production replacement: swap
_store for a persistent DB write and the get/save functions stay the same.
"""

from app.models.response import ReconciliationResponse

_store: dict[str, ReconciliationResponse] = {}


def save(response: ReconciliationResponse) -> None:
    _store[response.reconciliation_id] = response


def get(reconciliation_id: str) -> ReconciliationResponse | None:
    return _store.get(reconciliation_id)


def clear() -> None:
    """Remove all records. For use in tests only."""
    _store.clear()
