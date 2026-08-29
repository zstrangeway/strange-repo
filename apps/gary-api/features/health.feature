Feature: Health check
  As an operator of gary-api
  I want a health endpoint
  So that I can tell whether the service is up, and which build answered me

  Scenario: Service and database are healthy
    Given the service was built as release "b3d9f1c"
    When I GET "/health"
    Then the response status should be 200
    And the response body should be:
      """
      {"status": "ok", "database": "ok", "version": "b3d9f1c"}
      """

  Scenario: The database is unreachable
    Given the service was built as release "b3d9f1c"
    And the database is unreachable
    When I GET "/health"
    Then the response status should be 200
    And the response body should be:
      """
      {"status": "degraded", "database": "unavailable", "version": "b3d9f1c"}
      """

  Scenario: The build carries no release stamp
    Given the service was built with no release stamp
    When I GET "/health"
    Then the response status should be 200
    And the response body should be:
      """
      {"status": "ok", "database": "ok", "version": "unknown"}
      """
