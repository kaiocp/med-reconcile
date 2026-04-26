"""Allergy conflict detection with drug class cross-reactivity rules.

Checks a new prescription against a patient's documented allergies, including
known pharmacological cross-reactivity (e.g., a penicillin allergy implies
risk from amoxicillin-class drugs). This is a pure function: no I/O. The
caller provides the already-parsed allergy list from the adapter layer.
"""

from app.models.allergies import AllergyRecord
from app.models.response import AllergyConflict

# Maps allergen name (lowercase) → set of drug names (lowercase) that cross-react.
# Sulfonamides are deliberately omitted from Metformin's class: Metformin contains
# a sulfonamide moiety but is NOT a sulfonamide antibiotic. A documented sulfonamide
# allergy must not flag Metformin — a common clinical misconception.
CROSS_REACTIVITY_RULES: dict[str, set[str]] = {
    "penicillin": {"amoxicillin", "ampicillin", "penicillin"},
}


def check_allergy_conflicts(
    patient_allergies: list[AllergyRecord],
    new_prescription_drug_name: str,
) -> list[AllergyConflict]:
    """Return all allergy conflicts between the new prescription and documented allergies.

    Checks both direct allergen matches and known drug class cross-reactivity.
    Returns an empty list when no conflicts are detected.
    """
    drug_lower = new_prescription_drug_name.lower()
    conflicts: list[AllergyConflict] = []

    for allergy in patient_allergies:
        allergen_lower = allergy.allergen.lower()

        if drug_lower == allergen_lower:
            conflicts.append(
                AllergyConflict(
                    drug_name=new_prescription_drug_name,
                    allergen=allergy.allergen,
                    conflict_type="direct",
                )
            )
            continue

        cross_reactive = CROSS_REACTIVITY_RULES.get(allergen_lower, set())
        if drug_lower in cross_reactive:
            conflicts.append(
                AllergyConflict(
                    drug_name=new_prescription_drug_name,
                    allergen=allergy.allergen,
                    conflict_type="cross_reactivity",
                )
            )

    return conflicts
