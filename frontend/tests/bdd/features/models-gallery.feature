Feature: Models Gallery View
  Gallery/card view for the models list page with a card resize slider.

  Background:
    Given I am logged in as an admin
    And models exist in the system

  Scenario: Default view is list mode
    When I navigate to the models page
    Then I should see the models in list view
    And the list view toggle should be active

  Scenario: Switching to gallery view
    When I navigate to the models page
    And I click the gallery view toggle
    Then I should see the models as cards
    And the gallery view toggle should be active

  Scenario: Gallery cards show model details
    When I navigate to the models page
    And I click the gallery view toggle
    Then each card should show the model name
    And each card should show the model type

  Scenario: Resizing cards with the slider
    When I navigate to the models page
    And I click the gallery view toggle
    Then I should see the card size slider
    When I adjust the slider to maximum
    Then the cards should be larger

  Scenario: View preference persists across navigation
    When I navigate to the models page
    And I click the gallery view toggle
    And I navigate away and return to models
    Then I should see the models as cards

  Scenario: Slider is hidden in list view
    When I navigate to the models page
    Then I should not see the card size slider
