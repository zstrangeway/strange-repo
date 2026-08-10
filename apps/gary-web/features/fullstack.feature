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
  #
  # The providers are still stood in for, but by gary-api's own stand-in
  # rather than this suite's: a real page, at a real URL, that the browser
  # navigates to and back from exactly as it would with Google.

  Scenario: Signing in for the first time and being welcomed
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    Then I should be on the home page
    And the page shows "Welcome Home, Ada"

  Scenario: Signing in, out, and back to the same account
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I sign out
    Then I should be on the sign in page
    When I open the home page
    Then I should be on the sign in page
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    Then the page shows "Welcome Home, Ada"

  Scenario: Renaming myself
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the profile page
    And I change my display name to "Ada Lovelace"
    Then the page shows a confirmation
    When I open the home page
    Then the page shows "Welcome Home, Ada Lovelace"

  # The one that would catch gary-api and gary-web disagreeing about what an
  # identity is: the same address at a different provider must not find the
  # account the first one opened.
  Scenario: The same address at another provider is another account
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the profile page
    And I change my display name to "Ada Lovelace"
    And I sign out
    And I open the sign in page
    And I sign in with facebook, agreeing as "2|ada@example.com|Ada"
    Then the page shows "Welcome Home, Ada"

  Scenario: Connecting a second provider reaches the same account
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the profile page
    And I connect facebook, agreeing as "2|ada@example.com|Ada"
    Then facebook should be connected
    When I change my display name to "Ada Lovelace"
    And I sign out
    And I open the sign in page
    And I sign in with facebook, agreeing as "2|ada@example.com|Ada"
    Then the page shows "Welcome Home, Ada Lovelace"
