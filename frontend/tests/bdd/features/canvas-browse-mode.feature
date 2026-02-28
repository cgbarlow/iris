Feature: Browse Mode Canvas
  Read-only canvas for stakeholders with entity detail panel.

  Background:
    Given I am logged in as an admin
    And a model with canvas entities exists

  Scenario: Clicking a node shows entity details
    When I view the canvas in browse mode
    And I click on node "Payment Service"
    Then the entity detail panel should appear
    And I should see the entity type
    And I should see the entity description

  Scenario: Closing the entity detail panel
    Given the entity detail panel is showing
    When I click the close button on the panel
    Then the entity detail panel should not be visible

  Scenario: Nodes are not draggable in browse mode
    When I view the canvas in browse mode
    Then nodes should not be draggable
