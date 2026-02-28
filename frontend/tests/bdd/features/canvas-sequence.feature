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

  Scenario: Sequence diagram fits within container
    Given a model named "Zoom Flow" of type "sequence" with participants exists
    When I navigate to model "Zoom Flow"
    And I click the "Canvas" tab
    Then the sequence diagram should be visible
    And the sequence container should not overflow

  Scenario: Sequence diagram has zoom controls
    Given a model named "Zoom Controls Flow" of type "sequence" with participants exists
    When I navigate to model "Zoom Controls Flow"
    And I click the "Canvas" tab
    Then the sequence diagram should be visible
    And the sequence zoom controls should be visible

  Scenario: Sequence diagram edit mode shows toolbar
    Given a model named "Edit Flow" of type "sequence" with participants exists
    When I navigate to model "Edit Flow"
    And I click the "Canvas" tab
    And I click "Edit Canvas"
    Then the "Add Participant" button should be visible
    And the "Add Message" button should be visible
    And the "Save" button should be visible
    And the "Discard" button should be visible

  Scenario: Focus view expands canvas
    Given a model named "Focus Flow" of type "sequence" with participants exists
    When I navigate to model "Focus Flow"
    And I click the "Canvas" tab
    And I click "Focus"
    Then the focus view should be visible
    And I press Escape
    Then the focus view should not be visible
