Feature: API health display
  As an operator
  I want gary-web to show gary-api's health
  So that I can see at a glance whether the service is up

  Scenario: The API is healthy
    Given gary-api reports status "ok"
    When I open the home page
    Then the page shows the API status "ok"

  Scenario: The API cannot be reached
    Given gary-api is unreachable
    When I open the home page
    Then the page shows the API status "unavailable"
