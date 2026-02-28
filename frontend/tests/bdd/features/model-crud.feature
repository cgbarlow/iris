Feature: Model CRUD
  Model create, read, update, and delete operations.

  Background:
    Given I am logged in as an admin

  Scenario: Creating a model
    When I navigate to the models list
    And I click "New Model"
    And I fill in model name "New Architecture"
    And I select model type "Component"
    And I click "Create"
    Then "New Architecture" should appear in the model list

  Scenario: Filtering models by type
    Given models of different types exist
    When I navigate to the models list
    And I filter by type "UML"
    Then only UML models should be visible

  Scenario: Editing a model
    Given a model named "Old Model" exists
    When I navigate to model "Old Model"
    And I click "Edit"
    And I change the model name to "Updated Model"
    And I click "Save"
    Then the model name should be "Updated Model"

  Scenario: Deleting a model
    Given a model named "To Delete" exists
    When I navigate to model "To Delete"
    And I click "Delete"
    And I confirm deletion
    Then I should be on the models list page
