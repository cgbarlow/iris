Feature: Simple View Canvas
  Core canvas interactions for simple and component model types.

  Background:
    Given I am logged in as an admin
    And a model named "Test Architecture" of type "component" exists

  Scenario: Opening the canvas tab shows empty state
    When I navigate to model "Test Architecture"
    And I click the "Canvas" tab
    Then I should see the empty canvas message
    And a "Start Building" button should be visible

  Scenario: Entering edit mode
    When I navigate to model "Test Architecture"
    And I click the "Canvas" tab
    And I click "Start Building"
    Then the canvas editor should be visible
    And the "Add Entity" button should be visible

  Scenario: Adding a component entity to the canvas
    When I navigate to model "Test Architecture"
    And I click the "Canvas" tab
    And I click "Start Building"
    And I click "Add Entity"
    And I fill in entity name "Payment Service"
    And I select entity type "Component"
    And I click "Create"
    Then a node labelled "Payment Service" should appear on the canvas

  Scenario: Connecting two entities with a relationship
    Given the canvas has entities "Frontend" and "Backend API"
    When I connect "Frontend" to "Backend API"
    Then the relationship dialog should appear
    When I select relationship type "Uses"
    And I confirm the relationship
    Then an edge should connect "Frontend" to "Backend API"

  Scenario: Deleting a node removes connected edges
    Given the canvas has entity "A" connected to entity "B"
    When I select node "A"
    And I press the Delete key
    Then node "A" should not exist on the canvas
    And no edges should reference node "A"

  Scenario: Saving canvas persists data
    Given the canvas has entity "Service A"
    When I click "Save"
    And the save succeeds
    And I reload the page
    And I click the "Canvas" tab
    Then a node labelled "Service A" should appear on the canvas

  Scenario: Discarding changes reverts canvas
    Given the canvas has a saved entity "Service A"
    When I enter edit mode
    And I add entity "Temporary"
    And I click "Discard"
    Then node "Temporary" should not exist on the canvas
    And a node labelled "Service A" should appear on the canvas
