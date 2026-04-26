"""DrugBank-style drug-drug interaction lookup.

Severity values are DrugBank-native (``minor`` | ``moderate`` | ``major``).
The reconciliation service maps them to clinical severity downstream via a
deterministic mapping layer; no clinical-severity terms appear here.

The lookup is order-independent: ``check_interaction(a, b)`` returns the
same result as ``check_interaction(b, a)``. Unknown drug pairs return
``None`` — mirroring production behavior where absence of a record means
no known interaction."""


def _interaction(
    code_a: str,
    name_a: str,
    code_b: str,
    name_b: str,
    severity: str,
    contraindication: bool,
    description: str,
) -> dict:
    return {
        "drug_a": {"rxnorm_code": code_a, "name": name_a},
        "drug_b": {"rxnorm_code": code_b, "name": name_b},
        "drugbank_severity": severity,
        "contraindication": contraindication,
        "description": description,
        "evidence_level": 1,
    }


_INTERACTIONS: dict[frozenset[str], dict] = {
    frozenset({"67108", "11289"}): _interaction(
        "67108",
        "Enoxaparin",
        "11289",
        "Warfarin",
        "major",
        False,
        "Overlap of two anticoagulants during transition — increased bleeding "
        "risk. Requires careful monitoring of INR and anti-Xa levels.",
    ),
    frozenset({"11289", "36437"}): _interaction(
        "11289",
        "Warfarin",
        "36437",
        "Sertraline",
        "major",
        False,
        "SSRI increases warfarin plasma levels via CYP2C9 inhibition — "
        "significantly increased bleeding risk. INR monitoring required.",
    ),
    frozenset({"7417", "6585"}): _interaction(
        "7417",
        "Nifedipine",
        "6585",
        "Magnesium Sulfate",
        "major",
        False,
        "Both affect calcium channels. Concurrent use risks severe hypotension "
        "and neuromuscular blockade. Managed with close monitoring.",
    ),
    frozenset({"67108", "1191"}): _interaction(
        "67108",
        "Enoxaparin",
        "1191",
        "Aspirin (low-dose)",
        "major",
        False,
        "Anticoagulant + antiplatelet = additive bleeding risk. Co-prescribed "
        "in high-risk pregnancies when benefit outweighs risk.",
    ),
    frozenset({"36437", "5640"}): _interaction(
        "36437",
        "Sertraline",
        "5640",
        "Ibuprofen",
        "major",
        False,
        "SSRI + NSAID = significantly increased GI bleeding risk. Ibuprofen "
        "also avoided throughout pregnancy.",
    ),
    frozenset({"896762", "7417"}): _interaction(
        "896762",
        "Labetalol",
        "7417",
        "Nifedipine",
        "moderate",
        False,
        "Two antihypertensives — additive hypotension risk. Requires blood " "pressure monitoring.",
    ),
    frozenset({"6809", "7417"}): _interaction(
        "6809",
        "Metformin",
        "7417",
        "Nifedipine",
        "moderate",
        False,
        "Nifedipine may increase metformin absorption, affecting glycemic "
        "control. Monitor blood glucose.",
    ),
}


def check_interaction(rxnorm_code_a: str, rxnorm_code_b: str) -> dict | None:
    return _INTERACTIONS.get(frozenset({rxnorm_code_a, rxnorm_code_b}))
