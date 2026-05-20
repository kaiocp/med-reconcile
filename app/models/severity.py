"""Clinical and DrugBank severity enumerations shared across the model and service layers."""

from enum import StrEnum


class ClinicalSeverity(StrEnum):
    """Clinical severity levels used throughout the reconciliation workflow."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CONTRAINDICATED = "contraindicated"


class DrugBankSeverity(StrEnum):
    """DrugBank-native severity levels as returned by the interaction API."""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
