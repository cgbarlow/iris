Feature: Full View Canvas
  UML and ArchiMate diagram rendering via FullViewCanvas.

  Background:
    Given I am logged in as an admin

  Scenario: UML model shows UML canvas
    Given a model named "Class Diagram" of type "uml" exists
    When I navigate to model "Class Diagram"
    And I click the "Canvas" tab
    And I click "Edit Canvas"
    Then the UML canvas editor should be visible

  Scenario: ArchiMate model shows ArchiMate canvas
    Given a model named "Enterprise View" of type "archimate" exists
    When I navigate to model "Enterprise View"
    And I click the "Canvas" tab
    And I click "Edit Canvas"
    Then the ArchiMate canvas editor should be visible

  Scenario: Simple model shows simple canvas
    Given a model named "Basic Model" of type "simple" exists
    When I navigate to model "Basic Model"
    And I click the "Canvas" tab
    And I click "Edit Canvas"
    Then the simple canvas editor should be visible
