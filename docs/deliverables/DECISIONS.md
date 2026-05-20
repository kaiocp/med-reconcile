# Decisions Log — Medication Reconciliation Service

Engineering decisions log per Part 3 of the assessment. Each entry follows the four-part format (decision / alternatives / why / what to revisit) and is capped at 3–5 sentences. Entries are added as decisions are made; topics are grouped by area rather than strict chronology.

---

## CI pipeline and dev tooling

**Decision:** Single GitHub Actions workflow runs six sequential gates on every push and PR — Poetry install, Ruff lint, Ruff format check, mypy strict, pytest, pip-audit, Docker build — with one specific finding (CVE-2026-3219 against pip itself, no published fix as of this commit) explicitly ignored via `--ignore-vuln` and documented inline in the yaml. **Alternatives considered:** split lint/format/typecheck/test into parallel jobs (parallelism gain at the cost of install duplication and yaml verbosity); run pip-audit with no ignores (would block CI on a vuln we can't fix); skip pip-audit entirely (loses the security signal). **Why:** a single sequential job amortizes the Poetry install across all gates and produces one obvious pass/fail signal — parallelism isn't worth the cache-management complexity at this scale, and including the Docker build catches packaging issues (deps missing from `pyproject.toml`, files not copied) that lint and tests alone would miss. The pip-audit ignore is documented in the workflow with an instruction to reassess on every run, because silently dropping the audit (or pinning a known-vulnerable dep) trades visibility for green-CI optics — the wrong direction for clinical software. **Revisit:** when CVE-2026-3219 receives a published fix, remove the `--ignore-vuln` flag; if the suite grows past ~30s, consider splitting test execution into a parallel matrix while keeping lint/typecheck/audit in a shared setup job.

---

## Container packaging: multi-stage, non-root

**Decision:** Multi-stage Dockerfile on `python:3.11-slim` — builder stage installs deps via Poetry, runtime stage copies the installed packages into a minimal image and runs as a non-root `appuser` (uid 1000), with a Python-stdlib healthcheck wired into `docker-compose.yml`. **Alternatives considered:** single-stage build (simpler but ships Poetry and build tooling in the runtime image); container running as root; curl-based healthcheck (requires installing curl, increasing image size and attack surface). **Why:** multi-stage keeps the runtime image lean — no Poetry, no compilers — which reduces both attack surface and cold-start time, and non-root is table stakes for any container handling clinical data (running as root for convenience gets flagged in security review anyway). The `urllib`-based healthcheck avoids pulling curl into the image just to probe `/health`, keeping the runtime dependency footprint to what the service itself needs. **Revisit:** if the production deployment target dictates a specific base image (Distroless, Chainguard, or a client-mandated hardened image), the runtime stage swaps out without affecting the builder.


---

## Language and stack: Python + FastAPI + Poetry

**Decision:** Python with FastAPI for the service framework, Poetry for dependency management (pyproject.toml as the single config for project metadata, deps, Ruff, and mypy), Pydantic v2 for both request/response validation and structured LLM output schemas, with the virtualenv kept in-project (`poetry.toml` committed) so local and CI environments converge on the same layout. **Alternatives considered:** TypeScript with Next.js (path to a physician-facing UI in one deployment); Python with Flask + plain pip (lighter but no automatic OpenAPI generation, separate config files); Python with FastAPI but without Poetry (loses lockfile-based reproducibility). **Why:** the client already operates an EHR with its own UI, so the reconciliation service is a backend integration consumed by that UI — a bundled-frontend stack adds no value, while FastAPI delivers auto-generated OpenAPI docs (the integration handoff for the client's frontend team), Pydantic covers API validation and LLM structured outputs from a single schema source, and Poetry's lockfile + grouped dev deps make `poetry install` a one-command setup for any engineer picking up the project. **Revisit:** if a future scope adds a service-owned UI (admin tooling, monitoring dashboard), TypeScript becomes worth re-evaluating because the bundled-frontend advantage would then apply.

---

## Architecture: layered with adapters

**Decision:** Three-layer architecture with one-way dependencies (`api/` → `services/` → `adapters/`), where each external dependency — FHIR, drug interactions, allergy source, LLM — lives behind a concrete adapter module exposing a stable function signature; `services/` contains the pipeline orchestration and pure functions for severity mapping and validation. **Alternatives considered:** MVC (Model-View-Controller); full hexagonal architecture with abstract Port interfaces and dependency injection. **Why:** MVC's separation doesn't fit a pure API service (there's no presentation layer, just Pydantic JSON serialization, and Controller would conflate routing with pipeline orchestration that benefits from being split), and full hexagonal would add an abstract base class per adapter when each has a single concrete implementation — boilerplate without benefit at this scope. Layered + adapters delivers the same practical swappability (mock → real API is a module-level rewrite, not architectural) with less indirection, and formalizing Port interfaces remains a clean upgrade path if the service later supports multiple FHIR vendors or LLM providers simultaneously. **Revisit:** introduce explicit Port interfaces (ABCs) the first time the service genuinely needs two implementations of the same adapter (e.g., A/B testing LLM providers, multi-EHR support).

---

## Deterministic severity classification over LLM-based normalization

**Decision:** Severity classification uses a deterministic mapping table (`map_severity`) that translates DrugBank's three native levels into the five clinical levels the workflow requires; the CTO proposed using the LLM for this step, citing a mismatch between DrugBank's categories and what physicians expect. **Alternatives considered:** LLM-based severity classification using the patient's profile for context-sensitive normalization; inheriting DrugBank's categories directly without mapping. **Why:** severity is the primary signal physicians act on — "contraindicated" means stop, "low" means monitor — and that signal must be consistent and traceable to a deterministic source; an LLM producing probabilistic severity judgments cannot guarantee consistency, and the FDA's CDS guidance explicitly flags opaque classification as unlikely to qualify for the Non-Device CDS exclusion, which could reclassify the software as a medical device requiring premarket review. The deterministic mapping also means any adjustment to physician expectations is a one-line configuration change, not a prompt rewrite. **Revisit:** if DrugBank adds new native severity categories, `map_severity` raises `ValueError` rather than silently defaulting — production monitoring should alert on these so the mapping table stays current.

---

## Structured LLM outputs over free text

**Decision:** The LLM returns a JSON-schema-constrained response (`clinical_summary`, `medications_referenced`, `disclaimer`) rather than free text. **Alternatives considered:** free-text response parsed downstream with regex; unstructured prose with no schema constraint. **Why:** both OpenAI and Anthropic support schema-based structured outputs, making the pattern portable across providers; the `medications_referenced` field is the hook the deterministic validation layer uses to detect hallucinated medication names without NLP extraction from prose — free text was rejected because it shifts parsing complexity downstream and creates fragile regex dependencies. **Revisit:** if the schema needs additional validation fields (e.g., a `severity_claims` list for the severity-mismatch validator), add them here and update the validation layer concurrently.

---

## No LLM tool/function calling

**Decision:** Drug interaction checks, FHIR data fetching, and allergy reads are deterministic operations orchestrated by the service layer — they are not exposed as LLM tool calls. **Alternatives considered:** tool/function calling pattern where the LLM decides when to fetch data or check interactions. **Why:** making a clinical safety check a probabilistic decision (the LLM decides whether to check for interactions) is incompatible with the pipeline's deterministic-first architecture; the LLM receives pre-assembled, validated data and produces explanatory text — it never orchestrates. **Revisit:** no planned revision; this constraint is architectural, not a scope limitation.

---

## Temperature fixed at 0 for all clinical summary generation

**Decision:** Temperature is fixed at 0 for all LLM calls regardless of provider, model, or task variant. **Alternatives considered:** task-specific temperature tuning; provider-default temperature. **Why:** this is a patient safety decision — research shows significant diagnostic accuracy drops at higher temperature settings, and temperature 0 universally represents maximum determinism across providers (OpenAI's scale is 0–2, Anthropic's is 0–1). **Revisit:** if a future clinical NLP task genuinely requires variability (e.g., drafting alternative phrasings for patient-facing copy), introduce it as a separate, explicitly parameterised call — never change this constant.

---

## Model agnosticism via configuration parameter

**Decision:** The LLM provider is abstracted behind a `MODEL_IDENTIFIER` constant; switching models is a configuration change, not a code change. **Alternatives considered:** hardcoding `gpt-4o` as the model string; accepting the model as a function parameter per call. **Why:** peer-reviewed medical LLM benchmarks evolve rapidly — current literature validates GPT-4/GPT-4o but no GPT-5 clinical studies exist as of April 2026, and the cost landscape shifts with each model release; locking the service to a specific version creates technical debt the moment a new benchmark makes a different model preferable. **Revisit:** when a new model is validated for clinical summarisation, update `MODEL_IDENTIFIER` and add a DECISIONS.md entry noting the benchmark evidence.

---

## Prompt strategy: system/user split with SHA-256 hashing

**Decision:** The system prompt is a stable, module-level constant hashed with SHA-256 at import time (`SYSTEM_PROMPT_HASH`); the per-request user prompt is assembled via LangChain's `ChatPromptTemplate` with hard negative constraints embedded in the system prompt. **Alternatives considered:** plain f-string assembly per call; single-message prompt without a system/user split. **Why:** the hard constraints (never override severity, never recommend dosage changes, never reference medications not in the data) keep the LLM in the informing lane for FDA CDS Non-Device classification; the closed medication set in the user prompt reduces hallucination risk per published benchmarks; the stable hash is designed to satisfy 21 CFR Part 11 audit trail traceability — when the audit layer is built, attaching `SYSTEM_PROMPT_HASH` to each reconciliation record will allow every result to be traced back to the exact prompt version that produced it. **Revisit:** Implemented — `SYSTEM_PROMPT_HASH` is attached to every reconciliation audit record. If the system prompt changes, the hash changes automatically — document the clinical rationale for the change in this file.

---

## No auto-rewrite loop for failed LLM validation

**Decision:** If the LLM output fails validation, the response surfaces the validation flags and holds the summary for physician review — there is no corrective retry loop that attempts to rewrite the summary. **Alternatives considered:** retry-with-feedback loop where a validation failure triggers a second LLM call with corrective instructions. **Why:** temperature 0 means naive retries produce identical output; corrective retries add latency and cost for a fix the physician would make in seconds during mandatory review; a silently "fixed" summary that passes validation creates more risk than a flagged one because it removes the signal that something was off. **Revisit:** if production data shows a specific, correctable failure mode (e.g., disclaimer consistently dropped by a specific model version), a targeted single-retry is preferable to a general loop — but only after physician-review evidence confirms the corrective prompt reliably fixes it.

---

## Typed adapter contracts at the boundary

**Decision:** All three adapters return Pydantic models (`InteractionRecord`, `AllergyRecord`) or `Literal`-typed strings (`PregnancyStatus`, `AllergyDataStatus`) instead of raw `dict[str, Any]`; `get_pregnancy_status` validates the source value against the closed Literal set and raises `ValueError` on anything else. **Alternatives considered:** raw dicts (no compile-time safety); TypedDict (no runtime validation); cast without validation. **Why:** the adapter is the typing boundary — drift between the mock and the production API will land here, and Pydantic's runtime validation surfaces it loud, while `Literal` aliases give the service layer compile-time coverage on every branch (most importantly the contraindication overlay's pregnancy check). The trade-off is a small per-call instantiation cost, negligible compared to the network IO that production adapters will dominate. **Revisit:** when a real HTTP client replaces the mock, adapter bodies become `Model.model_validate(response.json())` — same model, different source, no service-layer change.

---

## Allergy adapter degraded path with broad except

**Decision:** `get_patient_allergies_safe` wraps the underlying CSV read in a broad `except Exception`, returning `([], "unavailable")` on any failure rather than propagating; the choice is verified by a `pytest.mark.parametrize` covering `OSError`, `ValueError`, and `KeyError`. **Alternatives considered:** catch specific exceptions only; let exceptions propagate and fail the whole reconciliation; one narrow negative test rather than parametrized. **Why:** the CTO's nightly-CSV-export setup makes malformed input realistic, and a clinical reconciliation must never crash because of a degraded auxiliary data source — the trade-off is opacity (we lose the specific exception type at the boundary), which the negative tests offset by pinning that the catch handles each realistic failure class. **Revisit:** if production logs surface a recurring specific exception, narrow the catch to that class so unexpected ones still surface, and add a parametrized case for it.

---

## Mocks bundled into the runtime Docker image

**Decision:** The Dockerfile copies both `app/` and `mocks/` into the runtime image so the assessment-scope adapters resolve at container boot. **Alternatives considered:** keep mocks out of the image and have adapters stub empty data; build two image variants (mock vs. production) gated by a build arg; switch adapters' import targets via environment variable at startup. **Why:** the assessment scope explicitly mocks every external API, so the deployable artifact for this engagement *is* the mock-backed service — splitting images or adding env-conditional import logic creates machinery that has to be torn out the moment a real adapter lands, and the eventual production rollout is a small, self-documenting Dockerfile change (drop `COPY mocks`, swap each adapter's internals). **Revisit:** when the first real adapter lands, make the `COPY mocks` line conditional on a build arg so the same Dockerfile produces both variants without duplication.

---

## mypy `ignore_missing_imports` for the `fhir.*` namespace

**Decision:** Added a mypy override to ignore missing type stubs for `fhir.resources.*` and `fhir.*`, accepting the third-party library's untyped surface rather than wrapping every FHIR construction in `cast()`. **Alternatives considered:** add explicit `cast()` calls at every FHIR boundary; pin to a `fhir.resources` version that ships complete stubs (none currently do); use `# type: ignore[import-not-found]` on each import line. **Why:** strict mypy on our own code is the goal — paying typing-noise across third-party FHIR boundaries we don't own buys nothing in safety, and the function-level signatures in `fhir_client.py` already pin the contract the service layer cares about. **Revisit:** if `fhir.resources` ships complete stubs in a future minor release, drop the override and let mypy infer end-to-end.

---

## LLM output validation uses deterministic string matching only

**Decision:** The validation layer (`summary_validator.py`) uses exact case-insensitive string matching and a static alias table — no LLM involvement, no probabilistic methods. **Alternatives considered:** a second LLM call to verify the first (a "judge" model pattern); fuzzy string matching (rapidfuzz, token_set_ratio with a 90% threshold). **Why:** a probabilistic validator could itself hallucinate, producing false negatives on exactly the checks that matter most; a false negative on a validation check (missing a hallucinated medication name) creates worse outcomes than no check at all, because it gives a false signal of cleanliness to the reviewing physician. The judge-model pattern adds latency, cost, and a second point of non-determinism. **Revisit:** if production logs show exact matching producing false positives on legitimate medication name variants, add fuzzy matching as a third lookup tier — but only with a labelled dataset of real outputs to tune the threshold against.

---

## Medication matching uses exact plus normalized alias matching; fuzzy matching deferred

**Decision:** The unrecognized-medication validator performs two lookups in sequence: (1) exact case-insensitive match against known names, (2) alias-table match resolving common brand names to generics. Both failing constitutes an unrecognized reference. **Alternatives considered:** fuzzy matching (rapidfuzz `token_set_ratio`, 90% threshold) as a third tier. **Why:** the mock LLM returns exact medication names drawn from the structured prompt data, so fuzzy matching would never trigger in the current test environment — adding it without observable test coverage would be dead, unexercised code. The alias table covers the clinically meaningful brand-to-generic mappings (Coumadin→warfarin, Tylenol→acetaminophen) that do occur in real LLM outputs. **Revisit:** when the real LLM adapter lands, instrument `medications_referenced` values against known names in production logs; if misspellings or partial names appear with non-trivial frequency, introduce fuzzy matching as a third tier with a labelled threshold.

---

## Disclaimer presence check added after empirical failure in temperature-0 testing

**Decision:** A dedicated `missing_disclaimer` validator checks for the phrase "pending physician review" in every generated summary, treating its absence as a critical flag regardless of other validation results. **Alternatives considered:** rely on the system prompt constraint alone (the prompt already mandates the disclaimer); add a retry if the disclaimer is absent. **Why:** during internal testing, GPT-4o-mini dropped the mandatory "pending physician review" disclaimer in 1 of 7 test scenarios at temperature 0 — prompt constraints are the first line of defense, but deterministic validation is the backstop; a summary reaching a prescriber without the disclaimer would remove the human-review gate entirely. Retry was rejected for the same reasons as the general no-auto-rewrite-loop decision (temperature 0 produces identical output on naive retry). **Revisit:** track disclaimer-absence rate in production; if it drops to zero across 1,000+ real calls, the check can be downgraded from critical to warning without removing it.

---

## Pregnancy-aware contraindication overlay (two-pass severity)
 
**Decision:** Severity assessment runs two deterministic passes in sequence: (1) `map_severity` translates DrugBank's native severity to a clinical level, (2) `maybe_promote_for_pregnancy` checks the patient's pregnancy status against a version-controlled teratogenic drug list and promotes to contraindicated when both conditions are met. **Alternatives considered:** a single-pass mapper with DrugBank's `contraindication` boolean flag set globally per drug pair; embedding pregnancy logic inside `map_severity`. **Why:** the same drug pair can be safe or dangerous depending on clinical context — Warfarin + Enoxaparin is a routine postpartum anticoagulant transition but is contraindicated during active pregnancy because Warfarin is teratogenic; a global flag would incorrectly contraindicate the postpartum case, which is a clinical falsehood. Two passes follow single-responsibility: the mapper handles API translation, the overlay handles clinical context. **Revisit:** extend the teratogenic drug list as new medications are added; if the overlay's logic grows beyond pregnancy (e.g., renal function, age), extract it into a general clinical-context module. The current overlay checks only the new prescription against the teratogenic list. If a pregnant patient is already on a teratogenic drug and a non-teratogenic drug is prescribed, the active medication's teratogenicity is not flagged — extending this requires a second pass over the active medication list.
 
---
 
## FHIR data modeling with `fhir.resources` R4B
 
**Decision:** Patient and MedicationRequest mock data uses the `fhir.resources` library (R4B sub-package) with Pydantic-based FHIR models, rather than hand-built dictionaries. **Alternatives considered:** plain dicts shaped to match FHIR; raw JSON fixtures loaded from files; custom Pydantic models mimicking FHIR structure. **Why:** the client's EHR exposes a FHIR R4-compliant API, and R4B is backward-compatible with R4 (Patient and MedicationRequest are unchanged between releases) — using the same Pydantic-based models the production integration would use means the mock data is structurally validated against the spec at construction time, and the production swap is a backend change in the adapter, not a schema migration. **Revisit:** if the client's FHIR API uses custom extensions or profiles, the `fhir.resources` models may need to be subclassed or wrapped to accommodate them.
 
---
 
## In-memory audit store with append-only production path
 
**Decision:** Reconciliation results are stored in an in-memory Python dict for this scope, with both POST (create) and GET (retrieve by ID) endpoints operational against it. **Alternatives considered:** SQLite for lightweight persistence within the assessment; skipping the GET endpoint entirely (only POST was explicitly required). **Why:** the functional requirements specify audit logging — implementing both endpoints proves the audit workflow end-to-end without adding database setup overhead to the 4-hour window; the data structures and access patterns are identical to what a persistent store would use, so migration is a backend swap. For production, I would recommend an append-only persistent database — Datomic's architectural immutability (no update/delete operations exist in the data model) is stronger than PostgreSQL's policy-based immutability (superusers can bypass RLS and disable triggers), which matters when audit trail integrity is a compliance requirement. **Revisit:** the retention policy should be defined with the client's compliance team — HIPAA recommends a 6-year minimum for audit records.
 
---
 
## Error detail sanitization at the API boundary
 
**Decision:** Pydantic validation errors are intercepted and translated into clinician-appropriate messages before reaching the API response — `string_pattern_mismatch` on `rxnorm_code` becomes "The medication code 'abc123' is not valid. RxNorm codes must be numeric," not Pydantic's raw `[{'type': 'string_pattern_mismatch', 'loc': ...}]`. **Alternatives considered:** pass Pydantic error details through unmodified (standard FastAPI behavior); suppress error details entirely and return only the HTTP status. **Why:** the API's consumers are clinical systems and clinical operators, not developers — raw validation internals like `ctx`, `loc`, and type identifiers are meaningless to that audience and could leak implementation details; suppressing details entirely leaves the consumer unable to fix the request. The same UX principle that drives frontend error messaging applies to backend API responses consumed by clinical systems. **Revisit:** as new Pydantic validators are added (e.g., RxNorm terminology lookup in production), add corresponding sanitization mappings so no raw error shape ever reaches the response.
 
---
 
## Allergy data freshness advisory appended to every clinical summary

**Decision:** Every clinical summary includes a physician-facing advisory about allergy data freshness, with distinct text depending on whether allergy data was available or unavailable at the time of reconciliation. **Alternatives considered:** returning allergy data silently without any staleness caveat; blocking the reconciliation entirely if allergy data is older than a defined threshold. **Why:** the CTO specified nightly CSV updates, which creates an inherent staleness window between export and consumption — returning data without surfacing that context shifts liability to the platform if a missed allergy causes harm; blocking the reconciliation penalises the physician for a system limitation outside their control. The advisory makes the data limitation visible without disrupting the clinical workflow. **Revisit:** if the allergy source migrates to a real-time API, the advisory text can be removed or softened — the advisory is a modifier appended to the summary template, not a routing branch, so removal is a one-line change.

---

## Pregnancy status as service-layer lookup, not FHIR resource
 
**Decision:** Pregnancy status is modeled as a service-layer Python dictionary keyed by patient ID, not as a FHIR Observation resource mock. **Alternatives considered:** adding a third FHIR resource type (Observation with LOINC 82810-3 "Pregnancy status") to the mock data layer. **Why:** pregnancy status for the three test patients is a single lookup value per patient — mocking a full FHIR Observation resource for this adds structural overhead without testing anything the simpler approach doesn't; the production path (query a FHIR Observation resource alongside Patient) is documented in the code as a comment. **Revisit:** when the service connects to a real FHIR server, `get_pregnancy_status` queries Observation resources directly — the adapter signature stays the same, only the internals change.

---

## Unknown pregnancy status defaults to not_pregnant
 
**Decision:** When a patient exists in FHIR but has no recorded pregnancy status, the pipeline defaults to `not_pregnant` rather than hard-failing or treating it as an explicit `unknown` state. **Alternatives considered:** hard-fail the reconciliation if pregnancy status is absent; introduce an `unknown` status that bypasses the contraindication overlay and adds a physician advisory. **Why:** blocking a reconciliation for every patient without a recorded pregnancy status would prevent the service from working for the majority of patients — male patients, pediatric patients, and any patient where pregnancy is not clinically relevant have no reason to have this field populated. Defaulting to `not_pregnant` ensures the contraindication overlay passes through at base severity, which is clinically safe (it only promotes, never demotes). **Revisit:** the better production approach is an explicit `unknown` status that threads through to the clinical summary as an advisory ("pregnancy status not recorded — verify before prescribing"), giving the physician visibility without blocking the workflow.
 
---
 
## Separate API boundary model and internal prescription model
 
**Decision:** `NewPrescription` (in `request.py`) is the API boundary model with Pydantic `Field` validators (e.g., `pattern=r"^\d+$"` on `rxnorm_code`), while `PrescriptionItem` (in `patient_context.py`) is the clean internal model with no validators; the orchestrator converts between them explicitly. **Alternatives considered:** pass `NewPrescription` directly into the service layer; use a single model with optional validators toggled by context. **Why:** validation belongs at the API boundary — the service layer should receive data that's already structurally valid, and coupling internal functions to API-specific validation constraints (like regex patterns) would mean changing a validation rule requires touching service-layer code that shouldn't care. The four-field duplication is the tradeoff for that separation. **Revisit:** if more internal models start mirroring API models, introduce a shared base class with the common fields and let each layer add its own constraints.