Feature: Comments
  Comment CRUD on model and entity detail pages.

  Background:
    Given I am logged in as an admin
    And a model named "Commented Model" exists

  Scenario: Adding a comment
    When I navigate to model "Commented Model"
    And I open the comments section
    And I type "This is a test comment"
    And I click "Post Comment"
    Then the comment "This is a test comment" should be visible

  Scenario: Editing a comment
    When I navigate to model "Commented Model"
    And I open the comments section
    And I type "Original text"
    And I click "Post Comment"
    And I click "Edit" on the comment
    And I change the comment to "Updated text"
    And I click "Save"
    Then the comment "Updated text" should be visible

  Scenario: Deleting a comment
    When I navigate to model "Commented Model"
    And I open the comments section
    And I type "To delete"
    And I click "Post Comment"
    And I click "Delete" on the comment
    Then the comment "To delete" should not be visible
