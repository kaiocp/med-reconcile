Feature: Drug interaction detection and physician review gate
  As a prescribing physician
  I need the reconciliation service to flag drug interactions between a patient's
  active medications and a new prescription, and to hold the AI-generated clinical
  summary for my review before any AI-generated content reaches the patient's chart.

  Scenario: A postpartum warfarin transition surfaces a high-severity SSRI interaction
    Given a postpartum patient with active prescriptions for Sertraline and Enoxaparin
    When a new prescription for Warfarin is submitted for that patient
    Then the report includes a high-severity interaction between Warfarin and Sertraline
    And the report includes a high-severity interaction between Warfarin and Enoxaparin
    And the clinical summary is marked as pending physician review
    And the audit record captures the model identifier and the prompt hash

  Scenario: Prescribing warfarin to a pregnant patient on enoxaparin is reported as contraindicated
    Given a pregnant patient with an active prescription for Enoxaparin
    When a new prescription for Warfarin is submitted for that patient
    Then the report includes a contraindicated interaction between Warfarin and Enoxaparin
    And the clinical summary is marked as pending physician review
    And the AI summary is not committed to the chart automatically
