"""LLM clinical summary adapter — prompt assembly, mock routing, and structured output.

Prompt assembly runs against the real LangChain ChatPromptTemplate in all code paths
(production parity). The LLM call itself is mocked: the assembled prompt data is routed
to one of three template renderers that produce physician-validated clinical language.

In production:
- Replace the mock routing block with a real provider call (OpenAI/Anthropic).
- Set temperature=0 (fixed — patient safety decision, see DECISIONS.md).
- Pass ``timeout_seconds`` as the provider's request timeout.
- MODEL_IDENTIFIER comes from the provider's response metadata rather than this constant.
"""

import logging

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from app.adapters.prompts.system_prompt import CLINICAL_SUMMARY_SYSTEM_PROMPT
from app.adapters.prompts.user_prompt import CLINICAL_SUMMARY_USER_PROMPT
from app.models.allergies import AllergyDataStatus
from app.models.llm_output import LLMOutputSchema
from app.models.patient_context import MedicationItem, PregnancyStatus, PrescriptionItem
from app.models.response import AllergyConflict, ProcessedInteraction

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

MODEL_IDENTIFIER: str = "gpt-4o-mock"

# Temperature is fixed at 0 for all clinical summary generation.
# This is a patient safety decision: research shows significant diagnostic
# accuracy drops at higher temperatures. Never vary this by task or provider.
TEMPERATURE: float = 0.0

# Built once at import time. In production the messages list goes to the provider.
_CHAT_PROMPT: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(CLINICAL_SUMMARY_SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(CLINICAL_SUMMARY_USER_PROMPT),
    ]
)

_DISCLAIMER: str = "This summary was generated with AI assistance and is pending physician review."
_ALLERGY_ADVISORY_AVAILABLE: str = (
    "Note: allergy records are sourced from a system that updates nightly. "
    "Please verify the patient's current allergy status before prescribing."
)
_ALLERGY_ADVISORY_UNAVAILABLE: str = (
    "Allergy screening could not be performed for this reconciliation. "
    "Please verify the patient's allergy status independently before prescribing."
)


# ---------------------------------------------------------------------------
# Prompt formatting helpers (private)
# ---------------------------------------------------------------------------


def _format_active_medications(active_medications: list[MedicationItem]) -> str:
    lines = [
        f"- {med.drug_name} (RxNorm: {med.rxnorm_code}), {med.dosage}" for med in active_medications
    ]
    return "\n".join(lines) if lines else "None on record."


def _format_interactions(interactions: list[ProcessedInteraction]) -> str:
    if not interactions:
        return "None detected."
    lines = [
        f"- {ix.medication_a} + {ix.medication_b} " f"({ix.severity} severity): {ix.description}"
        for ix in interactions
    ]
    return "\n".join(lines)


def _format_allergy_conflicts(allergy_conflicts: list[AllergyConflict]) -> str:
    if not allergy_conflicts:
        return "None detected."
    lines = []
    for conflict in allergy_conflicts:
        label = "cross-reactivity" if conflict.conflict_type == "cross_reactivity" else "direct"
        lines.append(
            f"- {conflict.drug_name} conflicts with documented "
            f"{conflict.allergen} allergy ({label})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mock template renderers (private)
# ---------------------------------------------------------------------------


def _render_interactions_template(
    new_prescription: MedicationItem,
    active_medications: list[MedicationItem],
    interactions: list[ProcessedInteraction],
    allergy_conflicts: list[AllergyConflict],
) -> str:
    """Template 1: one or more drug-drug interactions detected."""
    n = len(interactions)
    pairs = len(active_medications)

    lines: list[str] = [
        f"The reconciliation for **{new_prescription.drug_name}** identified "
        f"{n} drug interaction(s) across {pairs} medication pair(s) evaluated."
    ]

    for ix in interactions:
        if ix.severity == "contraindicated":
            lines.append(
                f"\n**{ix.medication_a} + {ix.medication_b}**: This combination is classified as "
                f"contraindicated during active pregnancy due to teratogenic risk. "
                f"{ix.description}"
            )
        else:
            lines.append(
                f"\n**{ix.medication_a} + {ix.medication_b}**"
                f" ({ix.severity} severity): {ix.description}"
            )

    if allergy_conflicts:
        lines.append("\n**Allergy concern(s) also detected:**")
        for conflict in allergy_conflicts:
            label = "cross-reactivity" if conflict.conflict_type == "cross_reactivity" else "direct"
            lines.append(
                f"- **{conflict.drug_name}** conflicts with a documented "
                f"**{conflict.allergen}** allergy ({label})."
            )

    return "\n".join(lines)


def _render_clean_template(
    new_prescription: MedicationItem,
    active_medications: list[MedicationItem],
) -> str:
    """Template 2: no interactions and no allergy conflicts."""
    n = len(active_medications)
    return (
        f"No drug-drug interactions were identified between "
        f"**{new_prescription.drug_name}** and the patient's {n} active medication(s). "
        f"{n} medication pair(s) were evaluated against the drug interaction database. "
        f"No allergy conflicts were detected."
    )


def _render_allergy_conflict_template(
    new_prescription: MedicationItem,
    allergy_conflicts: list[AllergyConflict],
) -> str:
    """Template 3: no interactions, but allergy conflict(s) detected."""
    lines: list[str] = [
        f"No drug-drug interactions were identified for **{new_prescription.drug_name}**. "
        f"However, the reconciliation identified the following allergy concern(s):"
    ]
    for conflict in allergy_conflicts:
        label = "cross-reactivity" if conflict.conflict_type == "cross_reactivity" else "direct"
        lines.append(
            f"- **{conflict.drug_name}** conflicts with a documented "
            f"**{conflict.allergen}** allergy ({label})."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_clinical_summary(
    patient_id: str,
    new_prescription: PrescriptionItem,
    active_medications: list[MedicationItem],
    interactions: list[ProcessedInteraction],
    allergy_conflicts: list[AllergyConflict],
    allergy_data_status: AllergyDataStatus,
    pregnancy_status: PregnancyStatus,
    timeout_seconds: float = 10.0,  # no-op in mock scope; wraps real API call in production
) -> LLMOutputSchema | None:
    """Generate a structured clinical summary for a medication reconciliation.

    Returns ``None`` if generation fails — the pipeline treats this as degraded success
    and returns all deterministic data without the clinical summary.
    """
    try:
        pairs_checked = len(active_medications)
        interaction_count = len(interactions)

        # Assemble the prompt using LangChain (production parity + prompt hash audit).
        # In production, pass the returned messages list to the provider SDK.
        _CHAT_PROMPT.format_messages(
            patient_id=patient_id,
            pregnancy_status=pregnancy_status,
            new_prescription_name=new_prescription.drug_name,
            new_prescription_rxnorm=new_prescription.rxnorm_code,
            new_prescription_dosage=new_prescription.dosage,
            active_medications_formatted=_format_active_medications(active_medications),
            interaction_count=interaction_count,
            pairs_checked=pairs_checked,
            interactions_formatted=_format_interactions(interactions),
            allergy_conflicts_formatted=_format_allergy_conflicts(allergy_conflicts),
            allergy_data_status=allergy_data_status,
        )

        # Route to mock template.
        if interactions:
            body = _render_interactions_template(
                new_prescription, active_medications, interactions, allergy_conflicts
            )
        elif allergy_conflicts:
            body = _render_allergy_conflict_template(new_prescription, allergy_conflicts)
        else:
            body = _render_clean_template(new_prescription, active_medications)

        # Allergy advisory — always appended, varies by data availability.
        advisory = (
            _ALLERGY_ADVISORY_AVAILABLE
            if allergy_data_status == "available"
            else _ALLERGY_ADVISORY_UNAVAILABLE
        )

        # Disclaimer is always the absolute final line of the summary.
        clinical_summary = "\n\n".join([body, advisory, _DISCLAIMER])

        # Parse medications_referenced from the rendered text — reflects what the
        # summary actually says, which is what the validation layer checks against.
        all_known = {med.drug_name for med in active_medications}
        all_known.add(new_prescription.drug_name)
        summary_lower = clinical_summary.lower()
        medications_referenced = sorted(name for name in all_known if name.lower() in summary_lower)

        return LLMOutputSchema(
            clinical_summary=clinical_summary,
            medications_referenced=medications_referenced,
            disclaimer=_DISCLAIMER,
            model_identifier=MODEL_IDENTIFIER,
        )

    except Exception as exc:
        logger.warning("generate_clinical_summary failed: %s", exc, exc_info=True)
        return None
