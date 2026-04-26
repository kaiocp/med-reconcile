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