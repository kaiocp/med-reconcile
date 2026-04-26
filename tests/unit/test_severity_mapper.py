"""Unit tests for the deterministic severity mapping layer."""

import pytest

from app.services.severity_mapper import ClinicalSeverity, map_severity


def test_maps_drugbank_minor_to_clinical_low() -> None:
    assert map_severity("minor") == ClinicalSeverity.LOW


def test_maps_drugbank_moderate_to_clinical_moderate() -> None:
    assert map_severity("moderate") == ClinicalSeverity.MODERATE


def test_maps_drugbank_major_to_clinical_high() -> None:
    assert map_severity("major") == ClinicalSeverity.HIGH


def test_handles_uppercase_input() -> None:
    assert map_severity("MAJOR") == ClinicalSeverity.HIGH


def test_handles_mixed_case_input() -> None:
    assert map_severity("Minor") == ClinicalSeverity.LOW


def test_raises_on_unknown_severity() -> None:
    with pytest.raises(ValueError, match="Unknown DrugBank severity"):
        map_severity("critical")


def test_raises_on_empty_string() -> None:
    with pytest.raises(ValueError, match="Unknown DrugBank severity"):
        map_severity("")


def test_none_is_not_a_valid_input() -> None:
    # "none" is the absence of an interaction — not a DrugBank severity level
    with pytest.raises(ValueError, match="Unknown DrugBank severity"):
        map_severity("none")


def test_contraindicated_is_not_a_valid_input() -> None:
    # "contraindicated" comes from the overlay, not the severity mapper
    with pytest.raises(ValueError, match="Unknown DrugBank severity"):
        map_severity("contraindicated")
