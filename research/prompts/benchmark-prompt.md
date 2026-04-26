I'm a software engineer building a medication reconciliation service for a technical assessment. The service checks drug interactions using a deterministic API (not an LLM), and then uses an LLM to generate a plain-language clinical summary that explains the interaction data to the prescribing physician. The LLM does NOT classify severity, detect interactions, or make clinical decisions — it only generates an explanatory summary from structured data that's already been determined.

I need you to act as an academic researcher and produce a benchmark analysis for this specific use case. The deliverable is a structured report with citations to peer-reviewed papers (prefer systematic reviews, meta-analyses, and papers from journals like Nature, NEJM, The Lancet, JAMA, npj Digital Medicine, or comparable venues).

Here's what I need benchmarked and researched:

## 1. Model Performance for Clinical Text Generation / Medical Summarization

Which foundation models perform best for generating accurate clinical summaries from structured medical data? I'm NOT asking about diagnosis or clinical reasoning — I'm asking about taking structured interaction data (drug A + drug B = high severity interaction due to X mechanism) and producing a safe, accurate plain-language explanation.

Compare at minimum: GPT-4o, GPT-5 / GPT-5.4 / GPT-5.5, Claude Sonnet 4 / Opus 4, Gemini 2.5, Med-PaLM 2, and any domain-specific medical models. I need accuracy metrics, hallucination rates, and safety metrics specifically for summarization/explanation tasks, not diagnostic tasks.

The client's CTO claimed "We're using GPT-4 for this; it's very accurate." I need evidence to either support or challenge this claim with actual benchmark data.

## 2. Temperature Settings and Clinical Safety

What does the research say about temperature settings for clinical/medical text generation? I need studies that measured accuracy, consistency, and safety at different temperature values.

Important nuance: different providers use different temperature scales (OpenAI uses 0-2, Anthropic uses 0-1, others may vary), but temperature=0 universally means "minimum randomness / maximum determinism" across all providers. The benchmark should establish that the principle of using minimum temperature applies regardless of provider, and that this is a patient safety decision, not a preference.

## 3. Output Length / Max Tokens for Clinical Summaries

Is there research on optimal length for clinical summaries presented to physicians? I'm currently planning to cap LLM output at 300-500 tokens. Is there evidence that:
- Shorter summaries improve physician comprehension and decision-making speed?
- Longer summaries provide better clinical coverage but risk information overload?
- There's a sweet spot for clinical text length that balances completeness with readability?

If there are no studies on this specifically for LLM-generated summaries, are there studies on physician reading behavior with clinical decision support alerts that could inform this decision?

## 4. Hallucination Rates in Medical Contexts

What are the measured hallucination rates for major LLMs in medical/clinical text generation tasks? I need:
- Overall hallucination rates in medical contexts
- Whether hallucination rates differ between summarization (explaining known facts) vs. reasoning (generating new conclusions)
- Any studies specifically on medication-related hallucinations (inventing drug names, incorrect interaction descriptions, fabricated clinical guidance)

## 5. LLM Safety in Regulated Clinical Workflows

Are there systematic reviews or position papers on the safety of using LLMs in clinical decision support workflows? Specifically:
- What safeguards does the literature recommend?
- Is there consensus on human-in-the-loop requirements?
- What validation methods are recommended for LLM output in clinical contexts?

## Deliverable Format

For each section, provide:
- The key finding in 2-3 sentences
- The specific papers that support it (title, authors, journal, year)
- The specific metrics or data points from those papers
- Any limitations or caveats in the evidence
- How this applies to my specific use case (medication reconciliation summary generation)

Prefer papers from 2023-2026. If a foundational older paper is essential, include it but flag the date.