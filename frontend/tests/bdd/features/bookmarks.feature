Feature: Bookmarks
  Bookmark toggle on model detail pages.

  Background:
    Given I am logged in as an admin
    And a model named "Bookmark Test" exists

  Scenario: Bookmarking a model
    When I navigate to model "Bookmark Test"
    And I click the "Bookmark" button
    Then the button should show "Bookmarked"

  Scenario: Removing a bookmark
    When I navigate to model "Bookmark Test"
    And I click the "Bookmark" button
    And I click the "Bookmarked" button
    Then the button should show "Bookmark"
