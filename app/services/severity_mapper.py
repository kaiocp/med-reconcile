"""Deterministic mapping from DrugBank native severity levels to clinical severity.

This is the alternative to LLM-based severity classification: every output
traces directly to the drug interaction API's data via an explicit, auditable
mapping table. The LLM explains severity in plain language; it does not decide
what the severity level is.
"""

from app.models.severity import ClinicalSeverity, DrugBankSeverity

__all__ = ["ClinicalSeverity", "DrugBankSeverity", "map_severity"]

_SEVERITY_MAP: dict[str, ClinicalSeverity] = {
    "minor": ClinicalSeverity.LOW,
    "moderate": ClinicalSeverity.MODERATE,
    "major": ClinicalSeverity.HIGH,
}


def map_severity(drugbank_severity: str) -> ClinicalSeverity:
    """Map a DrugBank native severity string to the corresponding clinical severity level.

    Input is normalized to lowercase before lookup. ``none`` and ``contraindicated``
    are not outputs of this function — ``none`` signals the absence of an interaction
    record (handled by the orchestrator) and ``contraindicated`` comes from the
    pregnancy-aware overlay applied after this mapping.

    Raises:
        ValueError: if the input does not match a known DrugBank severity level.
    """
    normalized = drugbank_severity.lower()
    result = _SEVERITY_MAP.get(normalized)
    if result is None:
        raise ValueError(
            f"Unknown DrugBank severity: '{drugbank_severity}'. "
            f"Expected one of: minor, moderate, major."
        )
    return result
