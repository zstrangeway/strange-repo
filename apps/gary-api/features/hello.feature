Feature: Hello world
  As a caller of gary-api
  I want a greeting endpoint
  So that I can confirm the service is up and responding

  Scenario: Greeting the world
    When I GET "/hello"
    Then the response status should be 200
    And the response body should be:
      """
      {"message": "Hello, World!"}
      """

  Scenario: Requesting an unknown path
    When I GET "/nope"
    Then the response status should be 404
