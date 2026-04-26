Feature: LLM output is validated against the patient's medication records
  As a prescribing physician
  I need the service to flag clinical summaries that reference medications
  outside the patient's known prescription set, so I am alerted to potential
  AI hallucinations before approving the summary.

  Scenario: The clinical summary always includes required safety advisories
    Given a fertility patient whose active medications are Metformin, Letrozole, and Progesterone
    And allergy data for that patient is available
    When a new prescription for Sertraline is submitted
    Then the clinical summary includes the AI-generated physician review disclaimer
    And the clinical summary includes an allergy data freshness advisory

  Scenario: The clinical summary references a medication the patient is not on
    Given a fertility patient whose active medications are Metformin, Letrozole, and Progesterone
    And a new prescription for Sertraline is submitted for that patient
    And the language model produces a clinical summary that also references Clopidogrel
    When the reconciliation pipeline runs
    Then the response includes a validation flag of type "unrecognized_medication"
    And the flag detail names Clopidogrel as the unrecognized medication
    And the audit record marks the validation status as flagged
