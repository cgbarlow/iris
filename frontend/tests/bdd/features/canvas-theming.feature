Feature: Canvas Theme Rendering
  Canvas renders correctly in all supported themes.

  Background:
    Given I am logged in as an admin
    And a model with entities on the canvas exists

  Scenario Outline: Canvas renders in <theme> theme
    Given I set the theme to "<theme>"
    When I view the canvas in browse mode
    Then the canvas should render without errors

    Examples:
      | theme          |
      | Light          |
      | Dark           |
      | High Contrast  |
