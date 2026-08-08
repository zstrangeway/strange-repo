Feature: Greeting endpoint
  As a client of example-api
  I want to request a greeting
  So that I can show it to a user

  Scenario: A client asks to be greeted by name
    Given the API is running
    When the client requests a greeting for "Zac"
    Then the response status is 200
    And the greeting message is "Hello, Zac!"

  Scenario: A client asks for a greeting without a name
    Given the API is running
    When the client requests a greeting with no name
    Then the response status is 200
    And the greeting message is "Hello, world!"

  Scenario: A client's name is padded with whitespace
    Given the API is running
    When the client requests a greeting for "  Zac  "
    Then the response status is 200
    And the greeting message is "Hello, Zac!"
