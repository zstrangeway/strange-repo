Feature: Health endpoint
  As an operator of example-api
  I want a health check
  So that I can tell whether the service is up

  Scenario: The service reports its health
    Given the API is running
    When the client requests the health check
    Then the response status is 200
    And the reported status is "ok"
