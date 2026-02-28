Feature: Entity CRUD
  Entity create, read, update, and delete operations.

  Background:
    Given I am logged in as an admin

  Scenario: Creating an entity
    When I navigate to the entities list
    And I click "New Entity"
    And I fill in entity name "Test Service"
    And I select entity type "Service"
    And I click "Create"
    Then "Test Service" should appear in the entity list

  Scenario: Editing an entity
    Given an entity named "Old Name" exists
    When I navigate to entity "Old Name"
    And I click "Edit"
    And I change the name to "New Name"
    And I click "Save"
    Then the entity name should be "New Name"

  Scenario: Deleting an entity
    Given an entity named "To Delete" exists
    When I navigate to entity "To Delete"
    And I click "Delete"
    And I confirm deletion
    Then I should be on the entities list page
