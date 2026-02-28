Feature: Model Creation Navigation

  Scenario: User creates a model and is taken to the model detail page
    Given I am logged in as an admin
    And I am on the models page
    When I click "New Model"
    And I fill in model name "Redirect Test Model"
    And I select model type "Simple"
    And I click "Create"
    Then I should be on the model detail page for "Redirect Test Model"
