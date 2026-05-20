"""Structured output schema for LLM clinical summary responses.

In production, this schema is sent to the LLM provider as a JSON schema constraint
(both OpenAI and Anthropic support schema-based structured outputs). The mock returns
data that conforms to it. The ``medications_referenced`` field is the hook the
validation layer uses to detect hallucinated medication names.
"""

from pydantic import BaseModel


class LLMOutputSchema(BaseModel):
    """Structured response from the LLM clinical summary generation."""

    clinical_summary: str
    medications_referenced: list[str]
    disclaimer: str
    model_identifier: str
