# US Health IT Regulatory Mapping for a Brazilian Biomedical Systems Engineer

## 1. Regulation-to-Regulation Mapping

### At a Glance

| ANVISA Regulation | US Counterpart(s) | Shared Principle | Key Divergence |
|---|---|---|---|
| **RDC 751/2022** — Medical Device Regulation | **FD&C Act §201(h) + 21 CFR Parts 800–898** — FDA device classification and premarket pathways | Risk-based classification; higher risk = more regulatory scrutiny | ANVISA uses 4 risk classes (I–IV); FDA uses 3 classes with multiple distinct premarket pathways (510(k), De Novo, PMA) |
| **RDC 665/2022** — Software as Medical Device (SaMD) | **21st Century Cures Act §3060 + FDA CDS Guidance + SaMD Clinical Evaluation Guidance** | IMDRF-derived SaMD framework; intended use determines classification | US has broad *statutory exclusions* for certain software (CDS, EHR, administrative); ANVISA treats SaMD classification as a more contained exercise |
| **RDC 657/2022** — Good Manufacturing Practices for Medical Devices | **21 CFR Part 820** — Quality System Regulation (QSR), transitioning to **ISO 13485** incorporation | Quality management systems; design controls; traceability | ANVISA is already ISO 13485-aligned; FDA's Part 820 is being revised to incorporate ISO 13485 by reference (effective Feb 2, 2026) — active convergence |

### Detailed Mapping

#### RDC 751 → FDA Device Classification Framework

Both regulations start from the same premise: the level of regulatory oversight should be proportional to the risk a device poses to patients. ANVISA's four-class system (I through IV) maps conceptually to FDA's three-class system, with ANVISA's Classes III and IV roughly splitting what the FDA combines into Class III.

The meaningful divergence is in premarket pathways. ANVISA has a relatively unified registration process where the requirements scale by risk class. The FDA fragments this into distinct pathways, each with its own logic:

- **510(k) — Premarket Notification (most Class II devices):** The manufacturer demonstrates "substantial equivalence" to a legally marketed predicate device. The regulatory question is: "Is this device similar enough to something already on the market?" This has no direct ANVISA parallel — ANVISA doesn't use the predicate device concept as the primary gatekeeping mechanism.
- **De Novo Classification (novel Class I/II devices):** For devices that are low-to-moderate risk but have no predicate. This pathway was created to prevent novel low-risk devices from being forced into the PMA process simply because nothing like them existed before.
- **PMA — Premarket Approval (Class III):** Full clinical evidence of safety and effectiveness. This is the closest to ANVISA's highest-risk registration requirements.

The practical implication: when evaluating whether a US-market software product needs premarket review, the first question isn't just "what risk class?" but "which pathway, and does a predicate exist?"

#### RDC 665 → Cures Act §3060 + FDA CDS Guidance

Both ANVISA's RDC 665 and the FDA's SaMD approach descend from the IMDRF SaMD framework, so the conceptual vocabulary is shared: intended use, significance of information provided, seriousness of the health condition. If you've worked with IMDRF risk categorization for ANVISA, the structure will feel familiar.

The critical US-specific element is the **21st Century Cures Act (2016)**, Section 3060, which *statutorily excludes* five categories of software from the device definition entirely:

1. Administrative support software
2. Software for maintaining/encouraging a healthy lifestyle
3. Electronic patient records
4. Software for transferring, storing, converting, or displaying data
5. **Clinical decision support that meets four specific criteria** (detailed in Section 3 below)

This is a fundamental structural difference from ANVISA. Under RDC 665, you classify software into a risk tier and apply proportional requirements. Under the US framework, there's a preliminary binary question — "Is this even a device at all?" — before you ever reach classification. Many software functions that ANVISA would classify as low-risk SaMD simply *aren't devices* in the US.

Beyond the statutory exclusions, the FDA layers **enforcement discretion** on top — meaning even some software that technically *is* a device may not be actively regulated, because the FDA has determined the risk doesn't justify enforcement. This is a distinctly US regulatory tool with no clean ANVISA equivalent.

#### RDC 657 → 21 CFR Part 820 (transitioning to ISO 13485)

This is the strongest convergence point. ANVISA's RDC 657 is already aligned with ISO 13485 for quality management systems. The FDA's 21 CFR Part 820 (Quality System Regulation) has historically been a US-specific QMS framework that was *conceptually similar* to ISO 13485 but structurally different — different terminology, different clause numbering, different emphasis areas.

That's changing. The FDA published a final rule revising Part 820 to incorporate ISO 13485:2016 by reference, effective February 2, 2026. Once effective, the quality system requirements for medical device manufacturers will be substantially harmonized between ANVISA and FDA. A manufacturer maintaining an ISO 13485-compliant QMS should be able to satisfy both regulators with a single quality system (with jurisdiction-specific addenda).

This is relevant for software development because both frameworks require design controls (design inputs, outputs, verification, validation, design transfer, design history file) — which means clinical software development must follow a controlled, documented lifecycle rather than ad-hoc development processes.

---

## 2. Electronic Records, Audit Trails, and Data Retention

The US regulatory landscape for electronic records in clinical systems is governed by several layered frameworks. Unlike ANVISA's relatively consolidated approach, these come from different agencies and address different concerns.

### 21 CFR Part 11 — Electronic Records; Electronic Signatures

This is the FDA regulation that most directly parallels ANVISA's traceability and electronic record integrity requirements under RDC 657. Part 11, first issued in 1997, establishes the criteria under which electronic records and electronic signatures are considered trustworthy, reliable, and equivalent to paper records.

**When it applies:** Part 11 applies to electronic records that are required by *predicate rules* — meaning other existing FDA regulations that require certain records to be maintained. Part 11 doesn't create new record-keeping obligations; it governs *how* those records must be managed when they're electronic. The key question is always: "Is there a predicate rule that requires this record?" If yes, and you keep the record electronically, Part 11 applies.

**Specific audit trail requirements (§11.10(e)):**

- Audit trails must be **computer-generated** — not manually created logs.
- Each entry must be **time-stamped** with a reliable, synchronized clock.
- The audit trail must independently record the **date and time** of operator entries and actions that **create, modify, or delete** electronic records.
- Record changes **must not obscure** previously recorded information — meaning the original values must remain visible and accessible even after modification.
- Each entry must capture: **who** (unique user identity), **what** (the specific action and data affected), **when** (timestamp), and **why** (reason for change).
- Audit trail documentation must be **retained for at least as long as** the underlying records they reference.
- Audit trails must be **available for agency review and copying**.

**Additional controls (§11.10):**

- **System validation:** Systems must be validated to ensure accuracy, reliability, consistent intended performance, and the ability to discern invalid or altered records.
- **Authority checks:** Only authorized individuals can use the system, sign records, alter records, or access specific functions. This means role-based access control with documented permission assignments.
- **Unique user identification:** No shared accounts. Every action must be attributable to a specific individual.
- **Electronic signatures (§11.50, §11.100, §11.200):** Must include the signer's printed name, date/time of signing, and the meaning of the signature (e.g., "Approved," "Reviewed," "Authored"). Each signing event requires fresh authentication — session-level login is not sufficient. Signatures must be permanently bound to the record.

**Design implications for a clinical software system:**

- The database schema needs immutable audit records — append-only, never updated or deleted.
- Every record mutation (create/update/delete) must trigger an audit event with user ID, timestamp, old value, new value, and reason for change.
- User authentication must enforce unique credentials — no shared service accounts for clinical operations.
- The system must have a documented validation lifecycle (IQ/OQ/PQ or equivalent risk-based approach, noting that FDA's Computer Software Assurance guidance from September 2025 allows risk-based proportionate evidence).

### HIPAA Security Rule (45 CFR Parts 160, 164)

HIPAA (Health Insurance Portability and Accountability Act) governs the privacy and security of Protected Health Information (PHI). Its Security Rule mandates administrative, physical, and technical safeguards for electronic PHI (ePHI).

**Key technical safeguards relevant to clinical software:**

- **Access controls (§164.312(a)):** Unique user identification, emergency access procedures, automatic logoff, encryption and decryption.
- **Audit controls (§164.312(b)):** Hardware, software, and procedural mechanisms to record and examine activity in information systems that contain or use ePHI. Note: HIPAA's audit requirements are less prescriptive than Part 11 — it requires the *capability* to audit but doesn't specify exact audit trail contents with Part 11's granularity.
- **Integrity controls (§164.312(c)):** Mechanisms to protect ePHI from improper alteration or destruction, including electronic mechanisms to corroborate that ePHI has not been altered.
- **Transmission security (§164.312(e)):** Encryption for ePHI in transit.

**Retention:** HIPAA requires security-related policies and documentation to be retained for **six years** from the date of creation or the date it was last in effect, whichever is later. This doesn't directly specify clinical record retention (that's governed by state laws, which vary), but it establishes a floor for security documentation.

**The Privacy Rule** governs who can access PHI, under what conditions, and what consent is required. It establishes the concept of "minimum necessary" — only the minimum amount of PHI needed for a specific purpose should be accessed.

### HITECH Act (Health Information Technology for Economic and Clinical Health Act, 2009)

HITECH extended HIPAA in important ways:

- **Business Associate liability:** Before HITECH, HIPAA's security requirements applied directly only to "covered entities" (healthcare providers, health plans, clearinghouses). HITECH made these requirements directly applicable to **business associates** — entities that handle PHI on behalf of covered entities. A software consultancy building a clinical system that processes patient data is almost certainly a business associate. This means:
  - You need a **Business Associate Agreement (BAA)** with every covered entity you serve.
  - You are **directly subject** to HIPAA's Security Rule, including audit controls and breach notification.
  - You face **direct enforcement** and penalties for violations — not just contractual liability to the covered entity.

- **Breach notification:** Expanded requirements for notifying individuals, HHS, and (for breaches affecting 500+ individuals) the media when unsecured PHI is breached.

### ONC Health IT Certification Program (45 CFR Part 170)

The Office of the National Coordinator for Health Information Technology (ONC) administers a certification program for health IT, primarily EHR systems. The certification criteria are codified at 45 CFR §170.315.

**Why this matters for a medication reconciliation service:**

If your service integrates with a certified EHR, the EHR must maintain its certification, which means your integration cannot compromise certified capabilities. Several criteria are directly relevant:

- **Clinical Decision Support / Decision Support Interventions (§170.315(a)(9) and §170.315(b)(11)):** The HTI-1 final rule introduced a new DSI criterion that requires transparency for AI/ML-based decision support. If your LLM-generated summaries are surfaced through the EHR, the platform must disclose source attributes — including that an AI-based intervention was used.
- **Drug-drug and drug-allergy interaction checks (§170.315(a)(4)):** Certified EHRs must already support interaction checking. Your medication reconciliation service should complement, not conflict with, existing certified capabilities.
- **Audit logging and auditable events (§170.315(d)(2) and §170.315(d)(3)):** Certified EHRs must support recording of auditable events and tamper-resistance for audit logs. Your service's audit trail should integrate with or complement the EHR's audit infrastructure.
- **Standardized APIs (§170.315(g)(10)):** The ONC requires FHIR-based APIs for patient and population services, using the SMART App Launch framework. If your service integrates via API, these standards apply.
- **USCDI (United States Core Data for Interoperability):** Version 3 became the baseline standard as of January 1, 2026. This defines the minimum data set for interoperability and affects what data your service must be able to consume and produce.

### How These Layer Together

Think of it as four dimensions of the same system:

| Dimension | Regulation | Core Question |
|---|---|---|
| **Privacy — who can see the data?** | HIPAA Privacy Rule + HITECH | Is this use of PHI authorized? Is only the minimum necessary being accessed? |
| **Security — is the data protected?** | HIPAA Security Rule + HITECH | Are there adequate administrative, physical, and technical safeguards? |
| **Integrity — can we trust the records?** | 21 CFR Part 11 | Are the electronic records authentic, unaltered, and traceable? Is every change attributed and time-stamped? |
| **Capability — what can the system do?** | ONC Certification (45 CFR §170.315) | Does the system meet required technical capabilities for interoperability, decision support, and audit logging? |

A medication reconciliation service must satisfy all four simultaneously. HIPAA governs access to the medication data. Part 11 governs the integrity of the reconciliation records. ONC certification governs the EHR platform's required capabilities. And if the service is itself a "device," the FDA's premarket framework applies on top.

---

## 3. FDA Classification of Clinical Decision Support Software

### The Four-Criteria Test

Under Section 520(o)(1)(E) of the FD&C Act (as amended by the 21st Century Cures Act), CDS software is **excluded from the device definition** — meaning it is *not* a medical device and requires *no* FDA premarket review — if it meets **all four** of the following criteria:

**Criterion 1 — No image/signal processing:**
The software is not intended to acquire, process, or analyze a medical image, a signal from an in vitro diagnostic device, or a pattern or signal from a signal acquisition system.

**Criterion 2 — Displays or analyzes medical information:**
The software is intended to display, analyze, or print medical information about a patient or other medical information (clinical guidelines, peer-reviewed literature, reference materials).

**Criterion 3 — Intended for HCP use with independent review:**
The software is intended for use by a healthcare professional (HCP) who can independently review the basis for the recommendations the software presents.

**Criterion 4 — Not intended for primary reliance:**
The software is intended for the HCP to use as one input among many — the software does not replace or direct the HCP's clinical judgment, and it is not the intent that the HCP rely primarily on the software's recommendations.

If **any one** criterion is not met, the software is potentially a device and subject to FDA oversight.

### Applying This to the LLM Medication Reconciliation Scenario

Walk through each criterion for a service that uses an LLM to generate clinical summaries from drug interaction data, presented to a clinician during medication reconciliation:

**Criterion 1 — LIKELY MET.** The service works with medication lists, pharmacy data, and drug interaction databases — not medical images or device signals. Unless the LLM is processing imaging data or diagnostic signals as inputs, this criterion is satisfied.

**Criterion 2 — LIKELY MET.** The service displays and analyzes medical information (drug interactions, patient medication history) and generates a summary. The sources are medical information about a patient and established drug interaction databases.

**Criterion 3 — THIS IS THE CRITICAL ONE.** The clinician must be able to "independently review the basis" for the LLM's recommendations. This means:

- The underlying drug interaction data that informed the summary must be **visible and accessible** to the clinician — not hidden behind the LLM's output.
- The clinician must be able to understand **why** the LLM produced the summary it did — which interactions were flagged, which sources were consulted, what reasoning was applied.
- For an LLM specifically, this creates a transparency requirement: the system should show the source data alongside the generated summary, not just the summary alone. If the LLM is a black box that produces a narrative without exposing its basis, Criterion 3 is at risk.

**Criterion 4 — DEPENDS ON ARCHITECTURE.** The software must be designed so that the clinician uses it as one input, not as the definitive answer. This is partly about system design (presenting the summary as a draft for review, not as a final determination) and partly about labeling/intended use (how the product is marketed and documented).

### The Auto-Commit Question

This is where architecture directly affects regulatory classification:

- **If the LLM summary is presented as a draft for clinician review** — the clinician reads it, can see the underlying interaction data, edits or approves it, and then commits it to the patient chart — you have a strong argument for non-device CDS under all four criteria.

- **If the LLM summary auto-commits to the patient chart** without clinician review — you've effectively removed the human-in-the-loop that Criteria 3 and 4 depend on. The software is no longer intended for an HCP to "independently review" — it's intended to act autonomously. This could push the software into device territory, requiring FDA premarket review.

This is not just a workflow convenience question — it's a regulatory classification question with material consequences.

### The 2026 CDS Guidance Update

The FDA issued a revised CDS guidance on January 6, 2026, which makes several updates relevant to this scenario:

- **Enforcement discretion for single-recommendation CDS:** The 2026 guidance expands enforcement discretion for CDS tools that provide a single clinically appropriate recommendation, as long as an HCP is in the loop and can review the basis. This is potentially favorable for a medication reconciliation tool that produces one summary per encounter.

- **Clinical documentation tools:** The guidance clarifies that software analyzing a clinician's findings to generate a proposed summary for a report may fall under enforcement discretion if a provider can independently review it. This is directly relevant to LLM-generated clinical summaries.

- **However — silence on AI/genAI specifics:** Despite being announced as AI-focused, the 2026 CDS guidance does not specifically address how generative AI products meet the CDS criteria, or how the FDA will regulate LLM-enabled clinical tools. This means continued regulatory uncertainty for this exact use case.

- **The guidance is non-binding.** It represents FDA's current thinking and intended enforcement approach, but it is not a regulation. A future administration or FDA leadership could change the agency's position.

### Comparison to ANVISA's RDC 665

Under RDC 665, the same software would be classified as SaMD and placed into a risk tier based on the IMDRF framework — considering the significance of the information provided and the seriousness of the health condition. The software would likely be classified as SaMD Class II or III (moderate risk) given that medication reconciliation affects treatment decisions for potentially serious conditions.

The key structural difference: under ANVISA, the software is *always* SaMD — the question is which risk tier. Under the FDA framework, the software might not be a device at all if it meets the four criteria. This means the US framework offers a potential path to *no premarket review whatsoever*, which doesn't exist under ANVISA's approach.

---

## 4. Recent Developments (2025–2026)

### FDA Actions

- **January 6, 2026 — Revised CDS Guidance:** Expanded enforcement discretion for single-recommendation CDS and clinical documentation tools. Removed the 2022 position that risk scores and risk probabilities categorically fail the non-device test. However, did not specifically address AI or generative AI CDS tools.

- **January 6, 2026 — Revised General Wellness Guidance:** Broadened the scope of non-invasive wearables and software that fall outside device regulation when marketed solely for general wellness purposes.

- **February 2, 2026 — Part 820 / ISO 13485 Harmonization:** The revised Quality System Regulation takes effect, incorporating ISO 13485:2016 by reference. This is a convergence point with ANVISA's existing framework.

- **2025 — FDA AI/ML Action Plan Updates:** The FDA published updated transparency requirements, including public submission summaries for AI/ML-enabled devices. The agency also created two cross-agency AI councils (External Policy for AI in regulated products, Internal Use for FDA's own AI adoption).

- **September 2025 — Computer Software Assurance (CSA) Guidance:** Changes how manufacturers demonstrate software validation compliance — allows risk-based proportionate evidence rather than exhaustive documentation. This doesn't change *what* Part 11 requires, but changes *how much evidence* you need to demonstrate compliance.

- **September 2025 — Request for Public Comment on AI Real-World Performance:** The FDA requested input on best practices for measuring and evaluating AI-enabled medical devices' real-world performance after deployment.

- **Forthcoming — New AI Regulatory Framework:** FDA Commissioner Makary announced that the agency is developing a "new regulatory framework for AI" that is "smarter and more forward-thinking." The revised Policy for Device Software Functions and Mobile Medical Applications is on the CDRH guidance agenda for FY2026. These future documents may more directly address genAI-enabled CDS.

### ONC / Health IT

- **January 1, 2026 — HTI-1 Compliance Deadline:** New ONC certification requirements took effect, including the DSI criterion (§170.315(b)(11)) requiring transparency for AI/ML-based decision support interventions, USCDI Version 3 as the baseline standard, and SMART App Launch v2. (Enforcement discretion extended to March 1, 2026 due to appropriations lapse.)

- **August 2025 — HTI-4 Final Rule:** New certification criteria for electronic prior authorization, electronic prescribing, and real-time prescription benefit information.

### Key Takeaway for AI-Enabled Clinical Software

The regulatory landscape for AI in clinical software is in active evolution. The FDA has signaled openness to reduced oversight for CDS tools where a clinician remains in the loop, but has not yet published guidance specifically addressing generative AI or LLM-based clinical tools. This means:

- **The "human-in-the-loop" design pattern is the safest architectural choice** — it keeps you in non-device CDS territory under current guidance.
- **Transparency of the AI's reasoning basis is essential** — both for FDA CDS criteria (Criterion 3) and for ONC DSI requirements.
- **Auto-committing AI-generated content to patient records carries regulatory risk** until the FDA specifically addresses genAI in clinical workflows.
- **The specific regulatory status of LLM-generated clinical summaries is genuinely unsettled.** Reasonable regulatory attorneys could disagree on whether a specific implementation meets the CDS criteria. This is an area where legal counsel with FDA digital health expertise should be consulted before making final architectural commitments.

---

## 5. Summary: What Transfers from ANVISA, What's New

| Concept | ANVISA Knowledge That Transfers | US-Specific Addition |
|---|---|---|
| Risk-based device classification | RDC 751 risk classes (I–IV) | FDA uses 3 classes + distinct premarket pathways (510(k), De Novo, PMA) |
| SaMD classification | RDC 665 / IMDRF framework | Cures Act §3060 creates statutory *exclusions* — software can be non-device entirely |
| Quality management systems | RDC 657 / ISO 13485 alignment | Part 820 converging to ISO 13485 (Feb 2026); the gap is closing |
| Audit trail requirements | RDC 657 traceability + electronic record integrity | 21 CFR Part 11 — same principles (who/what/when/why, immutability, retention) with US-specific procedural requirements |
| Electronic record integrity | ANVISA electronic record requirements | Part 11 + HIPAA Security Rule — layered: Part 11 for integrity, HIPAA for privacy/security |
| Clinical software regulation | RDC 665 SaMD framework | Four-criteria CDS test + enforcement discretion + ONC DSI transparency requirements |
| Interoperability standards | ANVISA TISS/TUSS standards | FHIR, USCDI v3, HL7 C-CDA, SMART App Launch v2 — ONC-mandated |

### Where to Acknowledge Limits

This mapping provides regulatory awareness, not legal advice. Specific areas where a healthcare compliance attorney should be consulted:

- Whether a specific LLM-based clinical software implementation meets the four CDS criteria under the Cures Act — this is a fact-specific legal determination.
- Whether Part 11 applies to specific records in a given implementation — this depends on which predicate rules apply.
- State-specific laws that may impose additional requirements on data retention, patient consent, or clinical software beyond the federal framework.
- The business associate determination under HIPAA/HITECH — while likely applicable, the specific contractual and compliance obligations should be reviewed by counsel.
- Whether the FDA's enforcement discretion positions, which are non-binding guidance, can be relied upon for product planning purposes.
