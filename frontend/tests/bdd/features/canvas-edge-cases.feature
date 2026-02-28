Feature: Canvas Edge Cases
  Edge case scenarios discovered during exploratory testing.

  Background:
    Given I am logged in as an admin

  Scenario: Deleting all entities returns to empty state
    Given a model with 3 entities on the canvas exists
    When I navigate to model "Multi Entity Model"
    And I click the "Canvas" tab
    And I click "Edit Canvas"
    And I delete all entities
    And I click "Save"
    And I click "Discard"
    Then I should see the empty canvas message

  Scenario: Save button is disabled without changes
    Given a model with entities on the canvas exists
    When I view the canvas in browse mode
    And I enter edit mode
    Then the "Save" button should be disabled

  Scenario: Unsaved changes indicator
    Given a model with entities on the canvas exists
    When I view the canvas in browse mode
    And I enter edit mode
    And I add entity "New Entity"
    Then I should see "Unsaved changes"
    When I click "Discard"
    Then I should not see "Unsaved changes"
