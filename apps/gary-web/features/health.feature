Feature: API health display
  As an operator
  I want gary-web to show gary-api's health and its database's
  So that I can see at a glance which of the two is in trouble

  Scenario: Everything is healthy
    Given gary-api reports status "ok" and database "ok"
    When I open the home page
    Then the page shows the API status "ok"
    And the page shows the database status "ok"

  Scenario: The database is unreachable
    Given gary-api reports status "degraded" and database "unavailable"
    When I open the home page
    Then the page shows the API status "degraded"
    And the page shows the database status "unavailable"

  Scenario: gary-api cannot be reached
    Given gary-api is unreachable
    When I open the home page
    Then the page shows the API status "unavailable"
    And the page shows the database status "unavailable"
