Feature: Email verification
  As a new user
  I want to confirm my address from the link gary emails me
  So that gary knows it can reach me, and stops asking

  Background:
    Given I am signed out

  Scenario: A new account is told it is unverified
    When I open the sign up page
    And I sign up as "Ada" with email "ada@example.com" and password "a long enough password"
    Then I should be on the home page
    And the page shows "Welcome Home, Ada"
    And the page shows an unverified notice

  Scenario: Following the link clears the notice
    Given an account already exists for "ada@example.com" with name "Ada" and password "a long enough password"
    And I am signed in as "Ada"
    When I open the verification link
    Then the page shows a confirmation
    When I open the home page
    Then the page does not show an unverified notice

  Scenario: A verified account is never nagged
    Given an account already exists for "ada@example.com" with name "Ada" and password "a long enough password"
    And "ada@example.com" has verified their address
    And I am signed in as "Ada"
    When I open the home page
    Then the page does not show an unverified notice

  Scenario: Asking for another link
    Given an account already exists for "ada@example.com" with name "Ada" and password "a long enough password"
    And I am signed in as "Ada"
    When I open the home page
    And I press "Send it again"
    Then the page shows a confirmation

  Scenario: A link that has already been used
    Given an account already exists for "ada@example.com" with name "Ada" and password "a long enough password"
    And the verification link has already been used
    When I open the verification link
    Then the page shows an error "That verification link has expired or has already been used"

  Scenario: An expired link
    Given an account already exists for "ada@example.com" with name "Ada" and password "a long enough password"
    And the verification link expired a day ago
    When I open the verification link
    Then the page shows an error "That verification link has expired or has already been used"

  # Verifying is not signing in, so the link has to work from whatever device
  # opened the email, which may be one gary has never seen.
  Scenario: Following the link while signed out
    Given an account already exists for "ada@example.com" with name "Ada" and password "a long enough password"
    When I open the verification link
    Then the page shows a confirmation
    When I sign in with email "ada@example.com" and password "a long enough password"
    Then the page does not show an unverified notice
