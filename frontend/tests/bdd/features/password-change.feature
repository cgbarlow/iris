Feature: Password Change
  Password change functionality on settings page.

  Background:
    Given I am logged in as an admin

  Scenario: Changing password successfully
    When I navigate to settings
    And I fill in current password
    And I fill in new password "NewSecurePass123"
    And I confirm new password "NewSecurePass123"
    And I click "Change Password"
    Then I should see a success message

  Scenario: Password mismatch shows error
    When I navigate to settings
    And I fill in new password "Password1234"
    And I confirm new password "DifferentPass12"
    And I click "Change Password"
    Then I should see "New passwords do not match"

  Scenario: Short password shows error
    When I navigate to settings
    And I fill in new password "Short1"
    And I confirm new password "Short1"
    And I click "Change Password"
    Then I should see "at least 12 characters"
