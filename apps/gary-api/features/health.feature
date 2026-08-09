Feature: Health check
  As an operator of gary-api
  I want a health endpoint
  So that I can tell whether the service is up before sending it traffic

  Scenario: Service reports itself healthy
    When I GET "/health"
    Then the response status should be 200
    And the response body should be:
      """
      {"status": "ok"}
      """
