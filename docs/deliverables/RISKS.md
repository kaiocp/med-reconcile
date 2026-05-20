# Risk Register — Medication Reconciliation Service

This document identifies risks across the client's requirements and kickoff context. Each risk is classified by the type of response it requires — some are safe to build with monitoring, some need pushback, and some require a fundamentally different approach.

---

## Requires a Fundamentally Different Approach

### 1. AI-generated content entering the chart without physician review

Unreviewed AI content in the patient's chart means a hallucinated drug name, an incorrect severity characterization, or a misleading recommendation becomes part of the official clinical record — and gets acted on. LLM benchmarks show hallucination rates of 1-3% even under optimal conditions. At scale, that's a consistent stream of errors no human reviewed.

This also has regulatory consequences: the FDA's CDS guidance requires that the healthcare professional can independently review the basis for recommendations. Removing that step could reclassify the feature as a regulated medical device, changing the product's entire premarket pathway. Without physician review, if AI-generated content contains an error, the liability sits entirely with the platform — there's no physician decision to trace it back to.

**Impact:** high. **Likelihood:** medium-high.
**Recommendation:** Hold AI summaries in a pending review state. Physician approves before anything reaches the chart. Design the review step for speed — in the common case, it's a single approval action.

### 2. LLM classifying interaction severity

Severity is the primary signal physicians act on — "contraindicated" means stop, "low" means monitor. An LLM severity judgment has no reviewable basis: the physician can't verify why the model chose "high" instead of "moderate." The additional suggestion to have the AI "pick the right severity based on the patient's profile" goes further — that's personalized clinical reasoning, not summarization.

Under the IMDRF risk framework, software that determines severity autonomously moves from "informing clinical management" to "driving clinical management" — a higher regulatory category. The FDA's 2026 CDS guidance explicitly flags opaque models as unlikely to qualify for the Non-Device CDS exclusion.

**Impact:** high. **Likelihood:** high — severity is assessed on every reconciliation.
**Recommendation:** Deterministic mapping layer translating the DrugBank API's categories to the five clinical levels. Transparent, auditable, consistent. The LLM explains severity in plain language; it never decides it.

### 3. Discarding reconciliation results after physician review

The functional requirements specify audit logging. Discarding results eliminates the audit trail for clinical decision support interactions. In the event of an adverse drug event, malpractice claim, or regulatory audit, there would be no record of what was flagged, what the physician saw, or what was approved. The HIPAA Security Rule requires audit controls for systems handling ePHI, with industry-standard retention of at least 6 years. If the EHR is subject to FDA oversight, 21 CFR Part 11 audit trail requirements also apply.

**Impact:** high. **Likelihood:** high — regulatory audits are routine for EHR platforms.
**Recommendation:** Retain all reconciliation results with full context. Define a retention policy aligned with the compliance minimum. Storage cost is negligible compared to liability exposure.

---

## Requires Pushback

### 4. Patient portal showing physician-facing clinical language

Clinical language written for a physician is inappropriate for patients — terms like "CYP2C9 inhibition" or "additive bleeding risk" are alarming without clinical context. Patients should only see content a physician has reviewed and approved.

**Impact:** medium. **Likelihood:** medium.
**Recommendation:** Scope the patient-facing layer as a follow-up. The physician review workflow creates the foundation — once a summary is approved, a patient-appropriate version with simplified language and disclaimers can be published through the portal.

### 5. GPT-4 as the specified model

GPT-4o outperforms GPT-4 on clinical summarization benchmarks at 12x cheaper input and 6x cheaper output. The service should be model-agnostic — locking to a specific model version creates technical debt the moment a better or cheaper option becomes available.

**Impact:** medium — cost and performance. **Likelihood:** certain — pricing and benchmarks are published.
**Recommendation:** Build the service model-agnostic. Start with GPT-4o or GPT-4.1. Revisit as new benchmarks emerge.

---

## Safe to Build, but Flag Risks

### 6. CSV-based allergy integration

The CSV works for the initial scope but carries two risks. **Stale data:** a patient allergy documented at 3pm won't appear until the next nightly import — a window where a contraindication check could return a false negative. **File reliability:** malformed CSVs, file locks during updates, encoding issues, or a missed export could cause silent failures.

**Impact:** high (stale data could miss a dangerous allergy). **Likelihood:** medium.
**Recommendation:** Build as specified. The service validates CSV structure on each read and returns an explicit warning when allergy data is unavailable rather than a silent gap. The clinical summary also includes a standing advisory to verify allergy status, acknowledging the nightly update limitation directly in the physician-facing output. When the LLM is unavailable, this advisory is absent — `allergy_data_status` is the fallback signal in that path. For production, migrate to a real-time allergy source. Understanding why allergy data isn't available through an API is an important scoping question.

---

## Regulatory and Compliance Risks

### 7. Business Associate liability under HITECH

Nolte, as the engineering partner building a service that processes ePHI, would likely be classified as a Business Associate. HITECH makes business associates directly liable for HIPAA violations — not just the covered entity. If the engagement proceeds without a BAA, Nolte assumes uncontracted liability.

**Impact:** high — direct legal liability for Nolte. **Likelihood:** medium.
**Recommendation:** Execute a BAA between Nolte and the client before development begins.

### 8. PHI handling gaps for production

The current scope uses mock data. Production deployment requires encryption at rest, field-level access controls, audit trail access restrictions, and TLS for all API communication. These are HIPAA prerequisites, not optional enhancements.

**Impact:** high. **Likelihood:** low in current scope, high if production proceeds without these controls.
**Recommendation:** Document as a production prerequisite. Do not deploy with real patient data until these safeguards are in place.

---

## Architectural Risks

### 9. LLM provider availability blocking clinical workflow

The clinical summary depends on a third-party LLM provider. Provider outages, rate limits, and latency spikes are well-documented. If the service blocks on the LLM call, the physician waits for a non-critical enhancement while the safety-critical interaction data is already available.

**Impact:** medium. **Likelihood:** medium.
**Recommendation:** The service returns all deterministic data (interactions, severity, allergy conflicts) regardless of LLM availability. If the LLM call fails or times out, the response includes all safety-critical data with an explicit note that the summary is unavailable. A reasonable timeout prevents the LLM call from blocking the clinical workflow.

### 10. Reconciliation service becoming a blocking dependency

If the EHR integrates the reconciliation service synchronously, a service outage could prevent physicians from completing prescriptions — a patient safety risk in itself.

**Impact:** high. **Likelihood:** low to medium.
**Recommendation:** The EHR integration should treat reconciliation as a non-blocking enhancement. The prescription workflow completes regardless. Results are surfaced when available.

### 11. RxNorm code validation gap

The service validates that RxNorm codes are structurally valid but does not verify they correspond to actual medications in the RxNorm terminology system. A structurally valid but nonexistent code would return "no interactions found," which could be mistaken for a clean check.

**Impact:** low-medium. **Likelihood:** low (EHR systems typically enforce valid codes).
**Recommendation:** Structural validation for the initial scope. For production, add a terminology service lookup to verify medication codes exist.

### 12. LLM validation framework maturity

The validation layer catches obvious hallucinations (unrecognized medication names, explicit severity contradictions) but may miss subtle ones (paraphrased severity claims, medication aliases). Current research frameworks for LLM validation in clinical workflows have been tested primarily in pilot deployments, not at scale.

**Impact:** medium — subtle hallucinations may reach the physician review step. **Likelihood:** low — physician review is the final safety gate.
**Recommendation:** Treat the validation layer as a first gate, not the only gate. A physician feedback mechanism (flagging suspicious outputs) would provide data for refining the validation over time.

---

## Ethical Risks

### 13. Automation bias in clinical decision-making

When a system presents AI-generated severity classifications or recommendations with confidence, physicians may defer without independent verification. The FDA's 2026 CDS guidance explicitly recognizes this as a clinically meaningful risk.

**Impact:** medium-high. **Likelihood:** medium.
**Recommendation:** The response includes both the clinical severity and the source severity (DrugBank native) so the physician can trace the assessment. AI summaries are clearly labeled as AI-generated and pending review. Validation flags call out discrepancies explicitly. These design choices keep the physician engaged as a critical evaluator.

---

### 14. Unexpected input from production APIs causing hard failures

All pure functions in the pipeline (severity mapping, contraindication overlay, allergy checking) raise explicit errors on unexpected input rather than silently defaulting. In production with real external APIs, this is a realistic scenario — DrugBank could add a new severity category, the FHIR API could return a resource shape the service hasn't seen. These would surface as 500 errors until the code is updated.

**Impact:** medium — the reconciliation fails entirely for affected drug pairs. **Likelihood:** low-medium — API schemas do change, usually with advance notice.
**Recommendation:** Production monitoring should alert on `ValueError` from pure functions so the mapping tables can be updated proactively. Failing loud is the correct behavior for clinical software — silent defaults are more dangerous than visible failures.