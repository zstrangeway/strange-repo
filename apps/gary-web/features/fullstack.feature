@fullstack
Feature: The whole thing, for real
  As someone about to deploy gary
  I want a few paths exercised against a real gary-api and a real database
  So that the stub agreeing with itself cannot be the reason the suite is green

  # Every other spec here drives an in-memory stub of gary-api, which was
  # written from the same understanding that produced gary-api and so cannot
  # notice the two drifting apart. These run a real gary-api on a throwaway
  # database, through the real migrations, and are deliberately few — they
  # cost a Postgres and a Python process to run.

  Scenario: Signing up and being welcomed
    Given I am signed out
    When I open the sign up page
    And I sign up as "Ada" with email "ada@example.com" and password "a long enough password"
    Then I should be on the home page
    And the page shows "Welcome Home, Ada"

  Scenario: Signing in and out
    Given I am signed out
    When I open the sign up page
    And I sign up as "Ada" with email "ada@example.com" and password "a long enough password"
    And I sign out
    Then I should be on the sign in page
    When I open the home page
    Then I should be on the sign in page
    When I sign in with email "ada@example.com" and password "a long enough password"
    Then the page shows "Welcome Home, Ada"

  Scenario: Renaming myself
    Given I am signed out
    When I open the sign up page
    And I sign up as "Ada" with email "ada@example.com" and password "a long enough password"
    And I open the profile page
    And I change my display name to "Ada Lovelace"
    Then the page shows a confirmation
    When I open the home page
    Then the page shows "Welcome Home, Ada Lovelace"

  # The one that needs the real mail seam: gary-api builds the link, the
  # console provider logs it, and the spec reads it back out of gary-api's
  # own output rather than being handed it.
  Scenario: Resetting a forgotten password
    Given I am signed out
    When I open the sign up page
    And I sign up as "Ada" with email "ada@example.com" and password "a long enough password"
    And I sign out
    And I open the password reset page
    And I ask for a reset link for "ada@example.com"
    And I open the reset link gary-api emailed
    And I set my new password to "an even better password"
    Then I should be on the sign in page
    When I sign in with email "ada@example.com" and password "an even better password"
    Then the page shows "Welcome Home, Ada"
