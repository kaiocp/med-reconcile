"""Per-request user prompt template for clinical summary generation.

Variables are filled at call time via LangChain's ChatPromptTemplate.
Unlike the system prompt, this template is not hashed — the audit artifact
is the stable system prompt; per-request inputs are part of the reconciliation record.
"""

CLINICAL_SUMMARY_USER_PROMPT: str = """\
Generate a clinical summary for the following medication reconciliation.

**Patient context:**
- Patient ID: {patient_id}
- Pregnancy status: {pregnancy_status}

**New prescription being evaluated:**
- {new_prescription_name} (RxNorm: {new_prescription_rxnorm}), {new_prescription_dosage}

**Patient's active medications:**
{active_medications_formatted}

**Drug interactions detected ({interaction_count} of {pairs_checked} pairs checked):**
{interactions_formatted}

**Allergy conflicts:**
{allergy_conflicts_formatted}

**Allergy data status:** {allergy_data_status}\
"""
