Feature: Connected accounts
  As someone who signs in with a provider
  I want to connect the others to the same account
  So that clicking the wrong button does not strand me in an empty one

  Background:
    Given I have signed in at google as "ada@example.com" named "Ada Lovelace"

  Scenario: My profile says what is connected
    When I open the profile page
    Then google should be connected
    And facebook should not be connected

  Scenario: Connecting a second provider
    Given facebook will say I am "ada@example.com" named "Ada Lovelace"
    When I open the profile page
    And I connect facebook
    Then facebook should be connected
    And google should be connected
    And the address bar carries no message
    And the address bar carries nothing the provider added

  Scenario: Either provider then reaches the same account
    Given facebook will say I am "ada@example.com" named "Ada Lovelace"
    And I open the profile page
    And I connect facebook
    And I change my display name to "Ada L"
    When I sign out
    And I sign in with facebook
    Then the page shows "Welcome Home, Ada L"

  Scenario: A provider already held by another account is refused
    Given an account already exists at facebook for "someone@example.com" named "Someone"
    And facebook will say I am "someone@example.com" named "Someone"
    When I open the profile page
    And I connect facebook
    # gary-web's words, not gary-api's. The API says which provider; this app
    # does not need to, because the row it is next to already says so.
    Then the page shows an error "That account is already connected to another gary account."
    And the address bar carries no message
    And facebook should not be connected

  Scenario: My only way in cannot be disconnected
    When I open the profile page
    Then I cannot disconnect google

  Scenario: Disconnecting one of two
    Given facebook will say I am "ada@example.com" named "Ada Lovelace"
    And I open the profile page
    And I connect facebook
    When I disconnect google
    Then google should not be connected
    And facebook should be connected
