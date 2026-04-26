"""Unit tests for the deterministic LLM output validation layer."""

import pytest

from app.models.llm_output import LLMOutputSchema
from app.models.response import ProcessedInteraction
from app.models.severity import ClinicalSeverity
from app.services.summary_validator import validate_llm_output

_DISCLAIMER = "This summary was generated with AI assistance and is pending physician review."

_CLEAN_SUMMARY = (
    "No drug-drug interactions were identified between Sertraline and the patient's active "
    f"medications. Allergy data is available and no conflicts were found. {_DISCLAIMER}"
)


def _make_output(
    summary: str = _CLEAN_SUMMARY,
    medications_referenced: list[str] | None = None,
) -> LLMOutputSchema:
    return LLMOutputSchema(
        clinical_summary=summary,
        medications_referenced=(
            medications_referenced
            if medications_referenced is not None
            else ["Sertraline", "Metformin"]
        ),
        disclaimer=_DISCLAIMER,
        model_identifier="gpt-4o-mock",
    )


def _make_interaction(
    med_a: str = "Warfarin",
    med_b: str = "Sertraline",
    severity: ClinicalSeverity = ClinicalSeverity.HIGH,
    source_severity: str = "major",
) -> ProcessedInteraction:
    return ProcessedInteraction(
        medication_a=med_a,
        medication_b=med_b,
        severity=severity,
        source_severity=source_severity,
        description="SSRI increases warfarin plasma levels via CYP2C9 inhibition.",
    )


def test_clean_output_returns_no_flags_and_passed_status() -> None:
    output = _make_output()
    known_names = ["Sertraline", "Metformin", "Letrozole"]
    flags, status = validate_llm_output(output, known_names, [], [])
    assert flags == []
    assert status == "passed"


def test_unrecognized_medication_raises_warning_flag() -> None:
    output = _make_output(
        summary=f"Clopidogrel may interact with Warfarin. {_DISCLAIMER}",
        medications_referenced=["Clopidogrel"],
    )
    flags, status = validate_llm_output(output, ["Warfarin"], [], [])
    assert status == "flagged"
    assert len(flags) == 1
    assert flags[0].type == "unrecognized_medication"
    assert flags[0].flag_severity == "warning"
    assert "Clopidogrel" in flags[0].detail


def test_alias_resolves_brand_name_to_known_generic() -> None:
    output = _make_output(
        summary=f"Coumadin dosing must be monitored. {_DISCLAIMER}",
        medications_referenced=["Coumadin"],
    )
    # "coumadin" aliases to "warfarin"; "warfarin" is in known names
    flags, status = validate_llm_output(output, ["Warfarin"], [], [])
    assert flags == []
    assert status == "passed"


def test_severity_mismatch_contradiction_term_raises_critical_flag() -> None:
    summary = (
        "The Warfarin–Sertraline interaction is generally well-tolerated in most patients. "
        + _DISCLAIMER
    )
    output = _make_output(summary=summary, medications_referenced=["Warfarin", "Sertraline"])
    flags, status = validate_llm_output(
        output, ["Warfarin", "Sertraline"], [], [_make_interaction()]
    )
    assert status == "flagged"
    mismatch_flags = [f for f in flags if f.type == "severity_mismatch"]
    assert len(mismatch_flags) >= 1
    assert mismatch_flags[0].flag_severity == "critical"
    assert "Warfarin" in mismatch_flags[0].detail
    assert "Sertraline" in mismatch_flags[0].detail
    assert "high" in mismatch_flags[0].detail


def test_missing_disclaimer_raises_critical_flag() -> None:
    output = _make_output(
        summary="No interactions found.",
        medications_referenced=["Sertraline"],
    )
    flags, status = validate_llm_output(output, ["Sertraline"], [], [])
    assert status == "flagged"
    disclaimer_flags = [f for f in flags if f.type == "missing_disclaimer"]
    assert len(disclaimer_flags) == 1
    assert disclaimer_flags[0].flag_severity == "critical"


def test_multiple_flags_coalesce_and_status_is_flagged() -> None:
    # Missing disclaimer + unrecognized medication
    output = _make_output(
        summary="Clopidogrel should be monitored.",
        medications_referenced=["Clopidogrel"],
    )
    flags, status = validate_llm_output(output, ["Warfarin"], [], [])
    assert status == "flagged"
    types = {f.type for f in flags}
    assert "unrecognized_medication" in types
    assert "missing_disclaimer" in types


def test_unrecognized_medication_check_is_case_insensitive() -> None:
    output = _make_output(
        summary=f"WARFARIN monitoring required. {_DISCLAIMER}",
        medications_referenced=["WARFARIN"],
    )
    flags, status = validate_llm_output(output, ["warfarin"], [], [])
    assert flags == []
    assert status == "passed"


def test_empty_medications_referenced_does_not_flag() -> None:
    output = _make_output(
        summary=f"No interactions identified. {_DISCLAIMER}",
        medications_referenced=[],
    )
    flags, status = validate_llm_output(output, ["Sertraline"], [], [])
    # Only missing_disclaimer could fire — disclaimer is present, so clean
    assert status == "passed"


def test_contraindicated_severity_triggers_mismatch_on_safe_term() -> None:
    summary = f"Warfarin can be used during pregnancy with monitoring. {_DISCLAIMER}"
    output = _make_output(summary=summary, medications_referenced=["Warfarin", "Enoxaparin"])
    interaction = _make_interaction(
        med_a="Warfarin",
        med_b="Enoxaparin",
        severity=ClinicalSeverity.CONTRAINDICATED,
        source_severity="major",
    )
    flags, status = validate_llm_output(output, ["Warfarin", "Enoxaparin"], [], [interaction])
    assert status == "flagged"
    mismatch = [f for f in flags if f.type == "severity_mismatch"]
    assert len(mismatch) >= 1
    assert "contraindicated" in mismatch[0].detail


def test_multiple_unrecognized_medications_produce_single_flag_with_all_names() -> None:
    output = _make_output(
        summary=f"Clopidogrel and Atorvastatin mentioned. {_DISCLAIMER}",
        medications_referenced=["Clopidogrel", "Atorvastatin"],
    )
    flags, status = validate_llm_output(output, ["Warfarin"], [], [])
    assert status == "flagged"
    unrec = [f for f in flags if f.type == "unrecognized_medication"]
    assert len(unrec) == 1
    assert "Clopidogrel" in unrec[0].detail
    assert "Atorvastatin" in unrec[0].detail


@pytest.mark.parametrize(
    "alias,generic",
    [
        ("Tylenol", "acetaminophen"),
        ("Advil", "ibuprofen"),
        ("Motrin", "ibuprofen"),
        ("Glucophage", "metformin"),
    ],
)
def test_common_brand_name_aliases_resolve_correctly(alias: str, generic: str) -> None:
    output = _make_output(
        summary=f"{alias} was mentioned. {_DISCLAIMER}",
        medications_referenced=[alias],
    )
    flags, _ = validate_llm_output(output, [generic], [], [])
    assert not any(f.type == "unrecognized_medication" for f in flags)
