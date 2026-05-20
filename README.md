# Medication Reconciliation Service

FastAPI service that compares a patient's active medications against a new prescription, flags drug–drug and allergy conflicts, and generates a physician-facing clinical summary.

> The implementation was completed within a 4-hour timebox. The commit timestamps reflect the actual coding window and can be verified via `git log --format='%ai %s'`. The remaining time was used exclusively for written deliverables and documentation — trackable via `docs:` conventional commits.

## Setup

**Prerequisites:** Python 3.11, [Poetry](https://python-poetry.org/) 1.8+.

```bash
poetry install                                  # install deps
poetry run uvicorn app.main:app                 # run dev server on :8000
poetry run pytest                               # ALL tests: unit, adapter, integration, BDD
poetry run ruff check .                         # lint
poetry run mypy app                             # typecheck (strict)
```

`poetry run pytest` runs the full suite — unit tests, adapter contract tests, integration tests, and Gherkin step definitions — in a single invocation. The same command runs in CI on every push (see [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)).

**Docker:**

```bash
docker compose up --build                       # service available on :8000
```

## Architecture

Three-layer pipeline with strict inward dependencies: **API → Services → Adapters**.

- **API** ([`app/api/`](./app/api/)) — FastAPI routes. Request validation, error shaping, no business logic.
- **Services** ([`app/services/`](./app/services/)) — pure, deterministic functions: severity mapping, allergy checks, pregnancy contraindication overlay, LLM-output validation, and the pipeline orchestrator ([`reconciliation.py`](./app/services/reconciliation.py)).
- **Adapters** ([`app/adapters/`](./app/adapters/)) — I/O boundaries: FHIR client, DrugBank client, allergy CSV reader, LLM client. Each can be swapped for a real backend; currently wired to the mocks in [`mocks/`](./mocks/).

The LLM is a **function inside a deterministic pipeline**: it receives structured inputs (interactions, allergy conflicts, pregnancy status) and produces prose in clinical language appropriate for a prescribing physician. It never orchestrates, never decides severity, and its output is validated before being returned to the caller. All clinically meaningful decisions (severity classification, pregnancy contraindication promotion, allergy matching) happen in pure Python services.

See [Pipeline Architecture](./docs/architecture.md) for the full request lifecycle, including failure modes and adapter boundaries.

```
med-reconcile/
├── app/
│   ├── main.py                # FastAPI entry, exception handlers
│   ├── api/routes.py          # POST/GET /api/v1/reconciliation
│   ├── services/              # pure logic: severity, allergy, validation, orchestrator
│   ├── adapters/              # FHIR, DrugBank, allergy CSV, LLM clients
│   │   └── prompts/           # system + user prompt templates, SHA-256 hash for audit
│   ├── models/                # Pydantic request/response/domain models
│   └── store/audit_store.py   # in-memory reconciliation store
├── mocks/
│   ├── fhir/                  # mock patients + MedicationRequests (FHIR R4B)
│   ├── drugbank/              # mock drug-interaction records
│   └── allergies/             # patient allergy CSV
├── tests/
│   ├── unit/                  # service-level tests
│   ├── integration/           # endpoint tests via httpx + TestClient
│   ├── features/              # pytest-bdd Gherkin scenarios
│   ├── step_defs/             # pytest-bdd step implementations
│   └── test_adapters.py       # adapter contract tests
└── docs/
    ├── architecture.md        # pipeline flow diagram (Mermaid)
    ├── deliverables/
    │   ├── PRODUCT-REVIEW.md
    │   ├── DECISIONS.md
    │   └── RISKS.md
    └── research/              # benchmark data and regulatory context
        ├── BENCHMARK.md
        ├── REGULATORY-CONTEXT.md
        └── prompts/           # prompts used for research artifacts
```

## Endpoints

| Method | Path                                   | Purpose                                       |
|--------|----------------------------------------|-----------------------------------------------|
| POST   | `/api/v1/reconciliation`               | Run a reconciliation; persists the result.    |
| GET    | `/api/v1/reconciliation/{id}`          | Fetch a previously stored reconciliation.     |
| GET    | `/health`                              | Liveness probe.                               |

Interactive Swagger UI: [`/docs`](http://localhost:8000/docs). OpenAPI JSON: `/openapi.json`.

## Testing the service

Start the service (`poetry run uvicorn app.main:app` or `docker compose up --build`), then use the Swagger UI at `/docs` or curl with these payloads. Each exercises a different scenario:

**1. Moderate interaction (Patient A + Nifedipine):**
```json
{
  "patient_id": "patient-001",
  "new_prescription": {
    "drug_name": "Nifedipine",
    "rxnorm_code": "7417",
    "dosage": "10mg PO q8h",
    "prescriber_id": "practitioner-001"
  }
}
```
Expected: 200, `pairs_checked: 3`, one moderate interaction (Labetalol + Nifedipine), no allergy conflicts.

**2. Penicillin allergy caught (Patient A + Amoxicillin):**
```json
{
  "patient_id": "patient-001",
  "new_prescription": {
    "drug_name": "Amoxicillin",
    "rxnorm_code": "723",
    "dosage": "500mg PO TID",
    "prescriber_id": "practitioner-003"
  }
}
```
Expected: 200, allergy conflict flagged (Penicillin → Amoxicillin cross-reactivity).

**3. Clean reconciliation, no sulfonamide false positive (Patient B + Sertraline):**
```json
{
  "patient_id": "patient-002",
  "new_prescription": {
    "drug_name": "Sertraline",
    "rxnorm_code": "36437",
    "dosage": "50mg PO daily",
    "prescriber_id": "practitioner-001"
  }
}
```
Expected: 200, zero interactions, zero allergy conflicts. Sulfonamide allergy does NOT flag metformin.

**4. Two high-severity interactions, postpartum (Patient C + Warfarin):**
```json
{
  "patient_id": "patient-003",
  "new_prescription": {
    "drug_name": "Warfarin",
    "rxnorm_code": "11289",
    "dosage": "5mg PO daily",
    "prescriber_id": "practitioner-002"
  }
}
```
Expected: 200, two high-severity interactions (Warfarin + Sertraline, Warfarin + Enoxaparin). No contraindication promotion — patient is postpartum.

**5. Patient not found:**
```json
{
  "patient_id": "patient-999",
  "new_prescription": {
    "drug_name": "Aspirin",
    "rxnorm_code": "1191",
    "dosage": "100mg PO daily",
    "prescriber_id": "practitioner-001"
  }
}
```
Expected: 404, `error_code: "patient_not_found"`.

**6. Invalid RxNorm code:**
```json
{
  "patient_id": "patient-001",
  "new_prescription": {
    "drug_name": "FakeDrug",
    "rxnorm_code": "abc123",
    "dosage": "10mg",
    "prescriber_id": "practitioner-001"
  }
}
```
Expected: 422, sanitized error message (not raw Pydantic internals).

**7. Empty patient ID:**
```json
{
  "patient_id": "",
  "new_prescription": {
    "drug_name": "Aspirin",
    "rxnorm_code": "1191",
    "dosage": "100mg PO daily",
    "prescriber_id": "practitioner-001"
  }
}
```
Expected: 422, sanitized error message.

## Key design decisions

- **Deterministic severity mapping, not LLM.** DrugBank severity strings are translated to clinical severity by a pure function ([`severity_mapper.py`](./app/services/severity_mapper.py)). The LLM is never asked to classify severity.
- **Physician review gate.** Every response includes `ai_disclaimer` ("pending physician review") and an `audit` block (model, prompt hash, temperature, validation status). The AI summary is always advisory.
- **Degraded success over hard failure.** Allergy CSV or LLM failures do not block the response — the caller still receives the deterministic interaction data with explicit `allergy_data_status` / `summary_status` fields so the UI can degrade gracefully. Only FHIR-level failures return 5xx.
- **LLM output is validated before the physician sees it.** [`summary_validator.py`](./app/services/summary_validator.py) checks for hallucinated drug names and severity terms that contradict the deterministic pipeline, attaching `validation_flags` to the response.

See [`docs/deliverables/DECISIONS.md`](./docs/deliverables/DECISIONS.md) for the full rationale.

## Assumptions

- **Mock data uses real RxNorm codes** and FHIR R4B resource shapes (`Patient`, `MedicationRequest`) — the adapters mirror what a real EHR integration would look like. Pregnancy status is modeled as a service-layer lookup; in production this would be sourced from a FHIR Observation resource (LOINC 82810-3).
- **Allergy data is CSV-backed** per the client's specification ([`mocks/allergies/allergies.csv`](./mocks/allergies/allergies.csv)), read through a dedicated adapter so it can be swapped for a real-time source without touching business logic.
- **Audit store is in-memory** ([`app/store/audit_store.py`](./app/store/audit_store.py)). In production this would be a persistent, append-only database — see [DECISIONS.md](./docs/deliverables/DECISIONS.md) for the rationale on storage strategy.
- **LLM client is mocked** but structured around the real LangChain message contract (`ChatPromptTemplate` with `SystemMessagePromptTemplate` + `HumanMessagePromptTemplate`); swapping in a provider requires changing only the adapter internals.
