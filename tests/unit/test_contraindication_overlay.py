"""Unit tests for the pregnancy-aware contraindication overlay."""

import pytest

from app.services.contraindication_overlay import (
    maybe_promote_for_pregnancy,
    pregnancy_contraindication_reason,
)
from app.services.severity_mapper import ClinicalSeverity

_WARFARIN_RXNORM = "11289"
_SERTRALINE_RXNORM = "36437"  # Non-teratogenic — used to verify pass-through


def test_promotes_warfarin_to_contraindicated_during_active_pregnancy() -> None:
    result = maybe_promote_for_pregnancy(
        ClinicalSeverity.HIGH, _WARFARIN_RXNORM, "active_pregnancy"
    )
    assert result == ClinicalSeverity.CONTRAINDICATED


def test_passes_through_severity_for_postpartum_patient() -> None:
    result = maybe_promote_for_pregnancy(ClinicalSeverity.HIGH, _WARFARIN_RXNORM, "postpartum")
    assert result == ClinicalSeverity.HIGH


def test_passes_through_severity_for_not_pregnant_patient() -> None:
    result = maybe_promote_for_pregnancy(ClinicalSeverity.HIGH, _WARFARIN_RXNORM, "not_pregnant")
    assert result == ClinicalSeverity.HIGH


def test_passes_through_severity_for_non_teratogenic_drug() -> None:
    result = maybe_promote_for_pregnancy(
        ClinicalSeverity.HIGH, _SERTRALINE_RXNORM, "active_pregnancy"
    )
    assert result == ClinicalSeverity.HIGH


def test_raises_on_unknown_pregnancy_status() -> None:
    with pytest.raises(ValueError, match="Unknown pregnancy status"):
        maybe_promote_for_pregnancy(ClinicalSeverity.HIGH, _WARFARIN_RXNORM, "trimester_1")


def test_returns_reason_for_teratogenic_drug() -> None:
    reason = pregnancy_contraindication_reason(_WARFARIN_RXNORM)
    assert reason is not None
    assert "contraindicated during active pregnancy" in reason
    assert "teratogenic risk" in reason
    assert "should not be used" not in reason  # avoid prescriptive language


def test_returns_none_for_non_teratogenic_drug() -> None:
    assert pregnancy_contraindication_reason(_SERTRALINE_RXNORM) is None
