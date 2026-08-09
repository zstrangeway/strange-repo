Feature: Profile
  As a signed-in user
  I want a page showing my details
  So that I can correct my name and change my password

  Background:
    Given an account already exists for "ada@example.com" with name "Ada" and password "a long enough password"

  Scenario: Viewing my profile
    Given I am signed in as "Ada"
    When I open the profile page
    Then the page shows my email "ada@example.com"
    And the page shows my display name "Ada"

  Scenario: A signed-out visitor cannot open a profile
    Given I am signed out
    When I open the profile page
    Then I should be on the sign in page

  Scenario: Changing my display name changes the welcome
    Given I am signed in as "Ada"
    When I open the profile page
    And I change my display name to "Ada Lovelace"
    Then the page shows a confirmation
    When I open the home page
    Then the page shows "Welcome Home, Ada Lovelace"

  Scenario: A blank display name is refused
    Given I am signed in as "Ada"
    When I open the profile page
    And I change my display name to "   "
    Then the page shows an error about the display name
    When I open the home page
    Then the page shows "Welcome Home, Ada"

  Scenario: Changing my password
    Given I am signed in as "Ada"
    When I open the profile page
    And I change my password from "a long enough password" to "an even better password"
    Then the page shows a confirmation
    When I sign out
    And I sign in with email "ada@example.com" and password "an even better password"
    Then I should be on the home page
    And the page shows "Welcome Home, Ada"

  Scenario: The current password is wrong
    Given I am signed in as "Ada"
    When I open the profile page
    And I change my password from "the wrong password" to "an even better password"
    Then the page shows an error "That is not your current password"
