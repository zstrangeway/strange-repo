Feature: Home
  As a signed-in user
  I want the home page to greet me by name
  So that I can see at a glance that gary knows who I am

  Scenario: A signed-in user is welcomed by name
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the home page
    Then the page shows "Welcome Home, Ada"

  Scenario: The welcome survives a reload
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the home page
    And I reload the page
    Then the page shows "Welcome Home, Ada"
