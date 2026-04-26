"""Reads ``allergies.csv`` on every call, by CTO directive — re-reading on each
request is the chosen behavior here and is flagged separately as a risk
(stale-data and IO-cost concerns belong in the project's RISKS document)."""

import csv
from pathlib import Path

_CSV_PATH = Path(__file__).parent / "allergies.csv"


def get_patient_allergies(patient_id: str) -> list[dict]:
    with _CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row["patient_id"] == patient_id]
