Feature: Password reset
  As a user who has forgotten my password
  I want to ask for a link from the sign in page
  So that I can get back in on my own

  Background:
    Given an account already exists for "ada@example.com" with name "Ada" and password "a long enough password"
    And I am signed out

  Scenario: Asking for a reset link
    When I open the sign in page
    And I follow "Forgotten your password?"
    And I ask for a reset link for "ada@example.com"
    Then the page shows "If that address has an account, a reset link is on its way"

  # The page cannot say whether the address was found, or it becomes a way to
  # ask gary who has an account.
  Scenario: An address with no account gets the same answer
    When I open the password reset page
    And I ask for a reset link for "nobody@example.com"
    Then the page shows "If that address has an account, a reset link is on its way"

  Scenario: Setting a new password from the link
    Given "ada@example.com" has been sent a reset link
    When I open the reset link
    And I set my new password to "an even better password"
    Then I should be on the sign in page
    And the page shows a confirmation
    When I sign in with email "ada@example.com" and password "an even better password"
    Then I should be on the home page
    And the page shows "Welcome Home, Ada"

  Scenario: The old password stops working
    Given "ada@example.com" has been sent a reset link
    When I open the reset link
    And I set my new password to "an even better password"
    And I sign in with email "ada@example.com" and password "a long enough password"
    Then I should still be on the sign in page
    And the page shows an error "Invalid email or password"

  Scenario: A link that has already been used
    Given "ada@example.com" has been sent a reset link
    And the link has already been used to set the password "an even better password"
    When I open the reset link
    Then the page shows an error "That reset link has expired or has already been used"

  Scenario: An expired link
    Given "ada@example.com" has been sent a reset link
    And the link expired an hour ago
    When I open the reset link
    Then the page shows an error "That reset link has expired or has already been used"

  Scenario: The new password is too short
    Given "ada@example.com" has been sent a reset link
    When I open the reset link
    And I set my new password to "short"
    Then the page shows an error about the password length
