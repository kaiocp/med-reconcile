# Medication Reconciliation Service

FastAPI service that compares a patient's active medications against a new prescription, flags drug–drug and allergy conflicts, and generates a physician-facing clinical summary.

> The implementation was completed within a 4-hour timebox. The commit timestamps reflect the actual coding window and can be verified via `git log --format='%ai %s'`.

## Setup

**Prerequisites:** Python 3.11, [Poetry](https://python-poetry.org/) 1.8+.

```bash
poetry install                                  # install deps
poetry run uvicorn app.main:app --reload        # run dev server on :8000
poetry run pytest                               # run tests (unit + integration + BDD)
poetry run ruff check .                         # lint
poetry run mypy app                             # typecheck (strict)
```

**Docker:**

```bash
docker compose up --build                       # service available on :8000
```

## Architecture

Three-layer pipeline with strict inward dependencies: **API → Services → Adapters**.

- **API** (`app/api/`) — FastAPI routes. Request validation, error shaping, no business logic.
- **Services** (`app/services/`) — pure, deterministic functions: severity mapping, allergy checks, pregnancy contraindication overlay, LLM-output validation, and the pipeline orchestrator (`reconciliation.py`).
- **Adapters** (`app/adapters/`) — I/O boundaries: FHIR client, DrugBank client, allergy CSV reader, LLM client. Each can be swapped for a real backend; currently wired to the mocks in `mocks/`.

The LLM is a **function inside a deterministic pipeline**: it receives structured inputs (interactions, allergy conflicts, pregnancy status) and produces prose. It never orchestrates, never decides severity, and its output is validated before being returned to the caller. All clinically meaningful decisions (severity classification, pregnancy contraindication promotion, allergy matching) happen in pure Python services.

```
med-reconcile/
├── app/
│   ├── main.py                # FastAPI entry, exception handlers
│   ├── api/routes.py          # POST/GET /api/v1/reconciliation
│   ├── services/              # pure logic: severity, allergy, validation, orchestrator
│   ├── adapters/              # FHIR, DrugBank, allergy CSV, LLM clients
│   │   └── prompts/           # system prompt + hash for audit
│   ├── models/                # Pydantic request/response/domain models
│   └── store/audit_store.py   # in-memory reconciliation store
├── mocks/
│   ├── fhir/                  # mock patients + MedicationRequests (FHIR R4B)
│   ├── drugbank/              # mock drug-interaction records
│   └── allergies/             # patient allergy CSV
├── tests/
│   ├── unit/                  # service-level tests
│   ├── integration/           # endpoint tests via httpx + TestClient
│   ├── features/ + step_defs/ # pytest-bdd scenarios
│   └── test_adapters.py       # adapter contract tests
└── deliverables/              # DECISIONS.md, PRODUCT-REVIEW.md
```

## Endpoints

| Method | Path                                   | Purpose                                       |
|--------|----------------------------------------|-----------------------------------------------|
| POST   | `/api/v1/reconciliation`               | Run a reconciliation; persists the result.    |
| GET    | `/api/v1/reconciliation/{id}`          | Fetch a previously stored reconciliation.     |
| GET    | `/health`                              | Liveness probe.                               |

Interactive Swagger UI: [`/docs`](http://localhost:8000/docs). OpenAPI JSON: `/openapi.json`.

## Key design decisions

- **Deterministic severity mapping, not LLM.** DrugBank severity strings are translated to clinical severity by a pure function (`severity_mapper.py`). The LLM is never asked to classify severity.
- **Physician review gate.** Every response includes `ai_disclaimer` ("pending physician review") and an `audit` block (model, prompt hash, temperature, validation status). The AI summary is always advisory.
- **Degraded success over hard failure.** Allergy CSV or LLM failures do not block the response — the caller still receives the deterministic interaction data with explicit `allergy_data_status` / `summary_status` fields so the UI can degrade gracefully. Only FHIR-level failures return 5xx.
- **LLM output is validated before the physician sees it.** `summary_validator.py` checks for hallucinated drug names/codes and severity terms that contradict the deterministic pipeline, attaching `validation_flags` to the response.

See [`deliverables/DECISIONS.md`](./deliverables/DECISIONS.md) for the full rationale.

## Assumptions

- **Mock data uses real RxNorm codes** and FHIR R4B resource shapes (`Patient`, `MedicationRequest`, `Observation` for pregnancy status) — so the adapters mirror what a real EHR integration would look like.
- **Allergy data is CSV-backed** per the assessment spec (`mocks/allergies/allergies.csv`), read through a dedicated adapter so it can be swapped for a real store without touching business logic.
- **Audit store is in-memory** (`app/store/audit_store.py`). In production this would be a persistent DB (Postgres) so reconciliation history survives restarts and can be audited across services.
- **LLM client is mocked** but structured around the real LangChain message contract; swapping in a provider (OpenAI, Anthropic, Bedrock) only requires changing the adapter.
