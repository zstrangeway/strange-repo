Feature: Signing in and out
  As someone with a Google, Facebook or Apple account
  I want to sign in with one of those
  So that gary never holds a password of mine to lose

  Scenario: The ways in are offered
    Given I am signed out
    When I open the sign in page
    Then google should be offered
    And facebook should be offered
    And apple should be offered

  Scenario: A first sign-in opens an account
    Given I have never signed in
    And google will say I am "ada@example.com" named "Ada Lovelace"
    When I open the sign in page
    And I sign in with google
    Then I should be on the home page
    And the page shows "Welcome Home, Ada Lovelace"

  Scenario: Signing in again returns to the same account
    Given I have signed in at google as "ada@example.com" named "Ada Lovelace"
    And I open the profile page
    And I change my display name to "Ada L"
    When I sign out
    And I sign in with google
    Then the page shows "Welcome Home, Ada L"

  # The visible consequence of not linking accounts by email address.
  Scenario: The same address at another provider is another account
    Given I have signed in at google as "ada@example.com" named "Ada Lovelace"
    And I open the profile page
    And I change my display name to "Ada L"
    And facebook will say I am "ada@example.com" named "Ada Lovelace"
    When I sign out
    And I sign in with facebook
    Then the page shows "Welcome Home, Ada Lovelace"

  Scenario: The greeting uses my name, not my address
    Given I have signed in at google as "ada@example.com" named "Ada Lovelace"
    When I open the home page
    Then the page shows "Welcome Home, Ada Lovelace"
    And the welcome does not show "ada@example.com"

  Scenario: A provider that will not vouch for me
    Given I am signed out
    And google will not say who I am
    When I open the sign in page
    And I sign in with google
    Then I should be on the sign in page
    And the page shows no error

  Scenario: A signed-out visitor is sent to sign in
    Given I am signed out
    When I open the home page
    Then I should be on the sign in page

  Scenario: A signed-in user has no reason to sign in again
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the sign in page
    Then I should be on the home page

  Scenario: The home page is closed again after signing out
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I sign out
    And I open the home page
    Then I should be on the sign in page

  Scenario: A deployment can offer fewer ways in
    Given I am signed out
    And only google and apple are offered
    When I open the sign in page
    Then google should be offered
    And facebook should not be offered
