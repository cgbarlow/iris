Feature: Sequence Diagram
  Sequence diagram rendering for sequence model types.

  Background:
    Given I am logged in as an admin

  Scenario: Sequence model renders sequence diagram
    Given a model named "Auth Flow" of type "sequence" with participants exists
    When I navigate to model "Auth Flow"
    And I click the "Canvas" tab
    Then the sequence diagram should be visible
    And I should see participant lifelines

  Scenario: Empty sequence shows placeholder
    Given a model named "Empty Sequence" of type "sequence" exists
    When I navigate to model "Empty Sequence"
    And I click the "Canvas" tab
    Then I should see the empty sequence message
