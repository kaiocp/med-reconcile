"""Deterministic validation of LLM-generated clinical summaries.

Pure functions — no I/O, no side effects. All checks use exact string matching
or alias tables; no probabilistic methods are used, because a validator that
could itself hallucinate would create worse outcomes than no check at all.
"""

from typing import Literal

from app.models.llm_output import LLMOutputSchema
from app.models.response import ProcessedInteraction, ValidationFlag

RXNORM_ALIASES: dict[str, str] = {
    "coumadin": "warfarin",
    "jantoven": "warfarin",
    "tylenol": "acetaminophen",
    "advil": "ibuprofen",
    "motrin": "ibuprofen",
    "glucophage": "metformin",
}

SEVERITY_CONTRADICTION_TERMS: dict[str, list[str]] = {
    "high": ["minor", "low-risk", "well-tolerated", "not significant", "negligible", "no concern"],
    "contraindicated": [
        "minor",
        "low-risk",
        "well-tolerated",
        "not significant",
        "safe",
        "no concern",
        "can be used",
    ],
    "moderate": ["no concern", "negligible", "not significant"],
}


def _check_unrecognized_medications(
    medications_referenced: list[str],
    known_medication_names: list[str],
) -> list[ValidationFlag]:
    known_lower = {n.lower() for n in known_medication_names}
    unrecognized: list[str] = []
    for drug in medications_referenced:
        drug_lower = drug.lower()
        if drug_lower in known_lower:
            continue
        resolved = RXNORM_ALIASES.get(drug_lower)
        if resolved is not None and resolved in known_lower:
            continue
        unrecognized.append(drug)

    if not unrecognized:
        return []

    names = ", ".join(unrecognized)
    verb = "is" if len(unrecognized) == 1 else "are"
    return [
        ValidationFlag(
            type="unrecognized_medication",
            detail=(
                f"The summary references {names}, which {verb} not in the patient's current "
                "medication records. Please verify before approving."
            ),
            flag_severity="warning",
        )
    ]


def _check_severity_mismatch(
    interactions: list[ProcessedInteraction],
    clinical_summary: str,
) -> list[ValidationFlag]:
    summary_lower = clinical_summary.lower()
    flags: list[ValidationFlag] = []
    seen: set[tuple[str, str, str]] = set()

    for interaction in interactions:
        severity_str = str(interaction.severity)
        contradiction_terms = SEVERITY_CONTRADICTION_TERMS.get(severity_str, [])
        for term in contradiction_terms:
            if term in summary_lower:
                key = (interaction.medication_a, interaction.medication_b, term)
                if key in seen:
                    continue
                seen.add(key)
                flags.append(
                    ValidationFlag(
                        type="severity_mismatch",
                        detail=(
                            f"The summary characterizes the {interaction.medication_a}–"
                            f'{interaction.medication_b} interaction as "{term}", but the drug '
                            f"interaction database classifies it as {severity_str}-severity. "
                            "Please review the severity assessment."
                        ),
                        flag_severity="critical",
                    )
                )
    return flags


def _check_missing_disclaimer(clinical_summary: str) -> list[ValidationFlag]:
    if "pending physician review" in clinical_summary.lower():
        return []
    return [
        ValidationFlag(
            type="missing_disclaimer",
            detail=(
                "The AI-generated summary is missing the required physician review disclaimer. "
                "This disclaimer must be present before the summary is shown to a prescriber."
            ),
            flag_severity="critical",
        )
    ]


def validate_llm_output(
    llm_output: LLMOutputSchema,
    known_medication_names: list[str],
    known_rxnorm_codes: list[str],
    interactions: list[ProcessedInteraction],
) -> tuple[list[ValidationFlag], Literal["passed", "flagged"]]:
    """Validate LLM output against patient medication records and safety rules.

    Returns (flags, validation_status). Status is 'passed' if flags is empty,
    'flagged' otherwise.
    """
    flags: list[ValidationFlag] = []
    flags.extend(
        _check_unrecognized_medications(llm_output.medications_referenced, known_medication_names)
    )
    flags.extend(_check_severity_mismatch(interactions, llm_output.clinical_summary))
    flags.extend(_check_missing_disclaimer(llm_output.clinical_summary))

    status: Literal["passed", "flagged"] = "flagged" if flags else "passed"
    return flags, status
