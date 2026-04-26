"""Unit tests for the allergy conflict checker."""

from app.models.allergies import AllergyRecord
from app.services.allergy_checker import check_allergy_conflicts


def make_allergy(allergen: str, severity: str = "moderate") -> AllergyRecord:
    return AllergyRecord(
        patient_id="patient-001",
        allergen=allergen,
        reaction_type="allergy",
        severity=severity,
        documented_date="2024-01-01",
    )


def test_flags_amoxicillin_for_penicillin_allergy() -> None:
    conflicts = check_allergy_conflicts([make_allergy("Penicillin")], "Amoxicillin")

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "cross_reactivity"
    assert conflicts[0].allergen == "Penicillin"
    assert conflicts[0].drug_name == "Amoxicillin"


def test_does_not_flag_metformin_for_sulfonamide_allergy() -> None:
    # Metformin contains a sulfonamide moiety but is not a sulfonamide antibiotic.
    # This is a physician-validated negative case — the service must not flag it.
    conflicts = check_allergy_conflicts([make_allergy("Sulfonamides")], "Metformin")
    assert conflicts == []


def test_flags_direct_allergen_match() -> None:
    conflicts = check_allergy_conflicts([make_allergy("Aspirin")], "Aspirin")

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "direct"


def test_returns_empty_for_no_allergies() -> None:
    assert check_allergy_conflicts([], "Amoxicillin") == []


def test_returns_empty_for_no_matching_allergy() -> None:
    assert check_allergy_conflicts([make_allergy("Latex")], "Amoxicillin") == []


def test_match_is_case_insensitive() -> None:
    conflicts = check_allergy_conflicts([make_allergy("PENICILLIN")], "amoxicillin")

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "cross_reactivity"


def test_only_matching_allergen_fires_when_multiple_documented() -> None:
    allergies = [make_allergy("Penicillin"), make_allergy("Latex")]
    conflicts = check_allergy_conflicts(allergies, "Amoxicillin")

    assert len(conflicts) == 1
    assert conflicts[0].allergen == "Penicillin"
