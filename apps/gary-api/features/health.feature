Feature: Health check
  As an operator of gary-api
  I want a health endpoint
  So that I can tell whether the service is up before sending it traffic

  Scenario: Service and database are healthy
    When I GET "/health"
    Then the response status should be 200
    And the response body should be:
      """
      {"status": "ok", "database": "ok"}
      """

  Scenario: The database is unreachable
    Given the database is unreachable
    When I GET "/health"
    Then the response status should be 200
    And the response body should be:
      """
      {"status": "degraded", "database": "unavailable"}
      """
