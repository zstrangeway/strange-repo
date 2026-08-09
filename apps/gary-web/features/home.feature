Feature: Home
  As a signed-in user
  I want the home page to greet me by name
  So that I can see at a glance that gary knows who I am

  Scenario: A signed-in user is welcomed by name
    Given I am signed in as "Ada"
    When I open the home page
    Then the page shows "Welcome Home, Ada"

  Scenario: The welcome uses my display name, not my email
    Given I am signed in as "Ada Lovelace" with email "ada@example.com"
    When I open the home page
    Then the page shows "Welcome Home, Ada Lovelace"
    And the page does not show "ada@example.com"

  Scenario: A signed-out visitor is sent to sign in
    Given I am signed out
    When I open the home page
    Then I should be on the sign in page

  Scenario: The welcome survives a reload
    Given I am signed in as "Ada"
    When I open the home page
    And I reload the page
    Then the page shows "Welcome Home, Ada"
