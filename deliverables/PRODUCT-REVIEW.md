# Product Review — Medication Reconciliation Service

**To:** CTO
**From:** Kaio Pedreira, Product Engineer (Nolte)
**Re:** Reconciliation feature — kickoff review and recommendations

---

Thank you for the walkthrough. The core idea is strong: a reconciliation service that sits between the existing EHR and a drug interaction database, flags potential problems, and gives physicians plain-language guidance before they prescribe. The existing FHIR R4 API gives us a solid integration foundation, and the reconciliation service fits naturally as a backend integration consumed by the EHR's existing interface.

Below is my assessment of what's sound, where I'd take a different approach, and what I'd need answered before we finalize scope.

---

## What I'd build as described

**The reconciliation endpoint and pipeline.** A service that receives a patient ID and a new prescription, retrieves active medications from the FHIR API, checks interactions against the drug interaction database, and returns a structured report with a well-documented API (OpenAPI/Swagger) for the EHR to consume.

**The AI-powered clinical summary.** Using an LLM to translate structured interaction data into plain-language guidance is the right use of the technology — the model explains, it doesn't decide. This is where AI genuinely saves physicians time. Before the summary reaches the physician, the service runs it through automated checks against the source data — if it references a medication the patient isn't taking, contradicts the severity returned by the interaction database, or drops the required review disclaimer, the summary is flagged for the physician's attention. This isn't distrust of the model; it's the principle behind any safety-critical system — verify the output before it reaches a human decision-maker.

**The CSV-based allergy integration — with a caveat.** I'll build this as specified. Two risks worth flagging: a nightly update creates a window where a newly documented allergy won't be reflected in results, and a malformed CSV could silently return no allergy data. The service would handle both cases explicitly — if allergy data is unavailable, the response says so rather than returning a silent gap. I'd recommend migrating to a real-time allergy source for production, and I have a question about this below.

---

## Where I'd take a different approach

**On severity classification: a deterministic mapping instead of the LLM.** The drug interaction API's categories don't match what physicians expect — that's a real problem that needs solving. I'd implement a deterministic mapping that translates the DrugBank API's three severity levels into the five clinical levels the workflow requires. Every output would trace directly to the API's data. If the mapping needs adjustment based on physician feedback, that's a configuration change, not a prompt rewrite.

I'd keep the LLM out of this for two reasons. First, severity is the primary signal physicians act on — a "contraindicated" label means stop, "low" means monitor. That signal needs to be consistent and traceable, which a deterministic function guarantees and a probabilistic model cannot. Second, the way severity is determined has implications for how the feature gets classified under FDA clinical decision support guidance. A transparent, verifiable severity source keeps the feature in a lighter regulatory category. An opaque model making severity judgments could push it into a higher one — which would change the product's regulatory posture significantly. The LLM adds value by explaining what a severity level means in context. It should not be the one deciding what the severity level is.

**On the model: GPT-4o instead of GPT-4.** Recent benchmarks show GPT-4o outperforms GPT-4 on clinical summarization at roughly one-tenth the cost — 12x cheaper on input, 6x cheaper on output. The service would be model-agnostic, so switching models is a configuration change. I've compiled the benchmark data and included it in the repository for reference.

---

## What I would not build in its current form

**AI-generated content flowing directly into chart notes without physician review.** I understand the goal is to minimize friction. Here's what I'd propose instead: the service generates the clinical summary and holds it for physician review. The physician sees the interaction report alongside the summary and can approve, edit, or reject. Only after approval does the content become eligible for the chart. In the common case where the summary is accurate, this is a single action — the friction is minimal.

This matters beyond patient safety. The way AI-generated content enters a clinical record has direct implications for the product's regulatory classification. The FDA's CDS guidance establishes that the healthcare professional must be able to independently review the basis for a recommendation — removing that step could reclassify the feature as a regulated medical device, which would fundamentally change the premarket requirements. The physician review step is what keeps this feature in the lighter regulatory category. It also assigns clinical responsibility to a licensed practitioner. Without it, if AI-generated content contains an error, the liability sits entirely with the platform — there's no physician decision to trace it back to.

**Discarding reconciliation results after physician review.** The functional requirements specify audit logging for all reconciliation requests. I'd implement persistent logging with full context — interaction data, AI summary, validation outcomes, timestamps, and the model version that generated each summary. This service would handle patient medication data, and HIPAA's audit-control requirements — among others in this space — call for trail retention well beyond the moment of physician review. I'd recommend retaining records for at least the minimum compliance period and defining the retention policy with input from a compliance professional. The storage cost is negligible compared to the exposure of having no audit trail during an adverse event investigation.

**Patients seeing the same AI summary the physician sees.** Different audiences need different language, detail levels, and disclaimers. More importantly, patients should only see content a physician has approved. The physician review workflow I've described creates the foundation for this: once content is approved, a patient-appropriate version can be published through the portal. I'd scope the patient-facing layer as a follow-up — the approval state would already be in the data model.

---

## Questions before scoping

1. **Allergy data source.** Why is allergy data in a CSV rather than available through a real-time service? Understanding whether this is a vendor limitation, a system migration, or an integration gap changes the architectural recommendation.

2. **Severity mapping validation.** The deterministic mapping I'm proposing needs to be reviewed with a clinician on your team to confirm it matches physician expectations. If specific interactions need different categorization, we adjust the mapping table — no code changes required.

3. **EHR integration pattern.** Should the reconciliation call be synchronous (the physician waits) or asynchronous (the prescription proceeds, results appear when ready)? I'd recommend treating the service as a non-blocking integration — it should never prevent a physician from completing a prescription if the service is slow or unavailable.

4. **Regulatory review.** Several of my recommendations reference FDA guidance and audit trail requirements. I'd recommend having a healthcare compliance professional review the service's regulatory posture before the feature reaches production — particularly the physician review workflow and the retention policy.
