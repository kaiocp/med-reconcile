"""Pregnancy-aware severity promotion overlay.

Runs after the severity mapper. Checks whether a new prescription should be
promoted to ``contraindicated`` based on the patient's pregnancy status and a
version-controlled teratogenic drug list. A global DrugBank contraindication
flag would incorrectly flag routine postpartum transitions (e.g., Warfarin +
Enoxaparin is standard care after delivery). This overlay applies the clinical
context deterministically.
"""

from app.services.severity_mapper import ClinicalSeverity

TERATOGENIC_DRUGS: dict[str, str] = {
    "11289": "Warfarin",  # RxCUI 11289
}

_VALID_PREGNANCY_STATUSES: frozenset[str] = frozenset(
    {"active_pregnancy", "not_pregnant", "postpartum"}
)


def maybe_promote_for_pregnancy(
    base_severity: ClinicalSeverity,
    new_prescription_rxnorm: str,
    pregnancy_status: str,
) -> ClinicalSeverity:
    """Promote severity to contraindicated for teratogenic drugs during active pregnancy.

    Returns ``base_severity`` unchanged for all other combinations.

    Raises:
        ValueError: if ``pregnancy_status`` is not a recognised value.
    """
    if pregnancy_status not in _VALID_PREGNANCY_STATUSES:
        raise ValueError(
            f"Unknown pregnancy status: '{pregnancy_status}'. "
            f"Expected one of: {sorted(_VALID_PREGNANCY_STATUSES)}."
        )
    if pregnancy_status == "active_pregnancy" and new_prescription_rxnorm in TERATOGENIC_DRUGS:
        return ClinicalSeverity.CONTRAINDICATED
    return base_severity


def pregnancy_contraindication_reason(rxnorm: str) -> str | None:
    """Return a clinical-language reason string if the drug is in the teratogenic list.

    Returns ``None`` for drugs not on the list.
    """
    drug_name = TERATOGENIC_DRUGS.get(rxnorm)
    if drug_name is None:
        return None
    return (
        f"{drug_name} is classified as contraindicated during active pregnancy "
        f"due to teratogenic risk."
    )
