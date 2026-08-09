Feature: Signing in and out
  As a registered user
  I want to sign in and sign out from the browser
  So that gary greets me on my own machine and forgets me when I leave

  Background:
    Given an account already exists for "ada@example.com" with name "Ada" and password "a long enough password"

  Scenario: Signing in
    Given I am signed out
    When I open the sign in page
    And I sign in with email "ada@example.com" and password "a long enough password"
    Then I should be on the home page
    And the page shows "Welcome Home, Ada"

  Scenario: The password is wrong
    Given I am signed out
    When I open the sign in page
    And I sign in with email "ada@example.com" and password "the wrong password"
    Then I should still be on the sign in page
    And the page shows an error "Invalid email or password"

  Scenario: The account does not exist
    Given I am signed out
    When I open the sign in page
    And I sign in with email "nobody@example.com" and password "a long enough password"
    Then I should still be on the sign in page
    And the page shows an error "Invalid email or password"

  Scenario: Signing out
    Given I am signed in as "Ada"
    When I open the home page
    And I sign out
    Then I should be on the sign in page

  Scenario: The home page is closed again after signing out
    Given I am signed in as "Ada"
    When I open the home page
    And I sign out
    And I open the home page
    Then I should be on the sign in page

  Scenario: A signed-in user has no reason to sign in again
    Given I am signed in as "Ada"
    When I open the sign in page
    Then I should be on the home page

  Scenario: gary-api cannot be reached
    Given I am signed out
    And gary-api is unreachable
    When I open the sign in page
    And I sign in with email "ada@example.com" and password "a long enough password"
    Then I should still be on the sign in page
    And the page shows an error "gary is unavailable, try again shortly"
