Feature: Signing up
  As a visitor
  I want to create an account
  So that I can use gary

  Scenario: Creating an account
    Given I am signed out
    When I open the sign up page
    And I sign up as "Ada" with email "ada@example.com" and password "a long enough password"
    Then I should be on the home page
    And the page shows "Welcome Home, Ada"

  Scenario: The email address is already taken
    Given an account already exists for "ada@example.com"
    And I am signed out
    When I open the sign up page
    And I sign up as "Ada" with email "ada@example.com" and password "a long enough password"
    Then I should still be on the sign up page
    And the page shows an error "That email address is already registered"

  Scenario: The password is too short
    Given I am signed out
    When I open the sign up page
    And I sign up as "Ada" with email "ada@example.com" and password "short"
    Then I should still be on the sign up page
    And the page shows an error about the password length

  Scenario: The email address is not an address
    Given I am signed out
    When I open the sign up page
    And I sign up as "Ada" with email "not-an-address" and password "a long enough password"
    Then I should still be on the sign up page
    And the page shows an error about the email address

  Scenario: A signed-in user has no reason to sign up
    Given I am signed in as "Ada"
    When I open the sign up page
    Then I should be on the home page
