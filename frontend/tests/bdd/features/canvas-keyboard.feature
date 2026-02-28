Feature: Canvas Keyboard Navigation
  WCAG 2.1.3 keyboard accessibility for all canvas operations.

  Background:
    Given I am logged in as an admin
    And a model with 3 entities on the canvas exists
    And I am in canvas edit mode

  Scenario: Tab cycles through nodes
    When I press Tab
    Then the first node should be focused
    When I press Tab again
    Then the second node should be focused

  Scenario: Arrow keys move selected node
    Given a node is selected
    When I press the right arrow key
    Then the node position should change

  Scenario: Ctrl+N opens new entity dialog
    When I press Ctrl+N
    Then the entity dialog should appear

  Scenario: Zoom controls via keyboard
    When I press Ctrl+=
    Then the canvas should zoom in
    When I press Ctrl+-
    Then the canvas should zoom out
    When I press Ctrl+0
    Then the canvas should fit to screen

  Scenario: Delete key removes selected node
    Given a node is selected
    When I press the Delete key
    Then the selected node should be removed

  Scenario: Escape clears selection
    Given a node is selected
    When I press Escape
    Then no node should be selected

  Scenario: C key toggles connect mode
    Given a node is selected
    When I press C
    Then connect mode should be active
    When I press Escape
    Then connect mode should be cancelled
