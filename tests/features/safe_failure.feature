Feature: Safe failure when upstream patient data is unavailable
  As a prescribing physician
  I need the service to fail visibly when it cannot retrieve the patient's data,
  because a partial response could be mistaken for a clean reconciliation and
  lead to a dangerous prescription decision.

  Scenario: The FHIR clinical records system is unreachable
    Given the FHIR clinical records system is unreachable
    When a reconciliation is requested for patient "patient-001"
    Then the service responds with a structured error
    And the error indicates that patient data could not be retrieved
    And no partial reconciliation result is returned
