I'm a Brazilian software engineer with a master's degree where my research line was "biomedical products and systems." During my master's, I studied Brazilian health technology regulations extensively — specifically ANVISA's RDC 751 (medical device regulation), RDC 665/2022 (software as medical device / SaMD), and RDC 657/2022 (good manufacturing practices for medical devices). I understand traceability requirements, electronic record integrity, audit trails, and clinical software classification from the Brazilian regulatory perspective.

I'm currently studying the US regulatory landscape for health IT and clinical software in order to expand my professional scope beyond the Brazilian framework. I want to leverage what I already know from ANVISA to build a solid understanding of the American equivalents.

Give me a comprehensive regulatory mapping from the Brazilian ANVISA framework I described to the US health IT and clinical software regulatory landscape. Specifically:

1. **Regulation-to-regulation mapping.** For each ANVISA regulation I mentioned (RDC 751, RDC 665/2022, RDC 657/2022), identify the closest US regulatory counterpart. For each pair, explain:
   - What shared regulatory principle connects them (e.g., risk-based classification, traceability, quality management systems).
   - Where they meaningfully diverge in scope, structure, or enforcement approach.
   - Whether there are areas of active convergence (e.g., ISO harmonization, IMDRF alignment).

2. **Electronic records, audit trails, and data retention in clinical systems.** Identify which US regulations govern the integrity of electronic health records, audit trail requirements, and data retention for clinical software. I need more than names — explain the specific technical and procedural requirements that would affect how a developer designs and builds a clinical software system (e.g., what must an audit trail capture, how long must records be retained, what constitutes a compliant electronic signature).

3. **Clinical decision support software classification.** I know ANVISA classifies SaMD through RDC 665's risk framework, which draws heavily from IMDRF. What's the US equivalent? Specifically:
   - When does clinical decision support (CDS) software become a "medical device" requiring FDA premarket review?
   - When is CDS software excluded from the device definition?
   - What are the specific statutory criteria for exclusion, and how are they interpreted in practice?
   - Apply this to a concrete scenario: a software service that uses an LLM to generate clinical summaries from drug interaction data for clinician review in a medication reconciliation workflow. Would this likely be classified as a device or non-device CDS, and what architectural decisions would affect that classification?

4. **Regulatory framework interactions.** In Brazil, ANVISA's framework is relatively consolidated — device regulation, SaMD classification, and quality management all flow from the same agency under a coherent structure. The US landscape appears more fragmented. Explain how the different US regulations governing health IT and clinical software interact with each other. I need to understand the layered structure: which regulation governs what dimension (privacy vs. data integrity vs. system capabilities vs. device classification), and how they stack rather than overlap.

5. **Recent developments (2025–2026).** Identify any recent regulatory changes or guidance updates that affect how AI-enabled clinical software is classified or regulated in the US. Focus on changes that would be material to someone building clinical software that integrates AI/LLM capabilities.

## How I want the response structured

- Lead with the mapping table so I can see the Brazilian-to-US pairs at a glance.
- For each mapping, explain the *reasoning* behind the regulatory parallel — not just "X maps to Y" but "X maps to Y because both address the same fundamental concern, which is..."
- When explaining requirements, be specific enough that I could use the information to make architectural decisions in a software system (e.g., "the audit trail must capture X, Y, and Z" rather than "audit trails are required").
- For the CDS classification section, walk through the criteria step by step using the LLM medication reconciliation scenario as a running example.
- For the framework interactions section, explain how the regulations layer rather than listing them in isolation.
- Flag any areas where the regulatory landscape is genuinely unsettled or where reasonable people disagree on interpretation.
- Distinguish between binding regulations, guidance documents (non-binding but influential), and enforcement discretion policies.
