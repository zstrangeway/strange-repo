Feature: Greeting the visitor
  As a visitor of example-web
  I want to be greeted by name
  So that the page feels like it is talking to me

  Scenario: A visitor gives their name
    Given the visitor is named "Zac"
    When the greeting is built
    Then the greeting reads "Hello, Zac!"

  Scenario: A visitor gives no name
    Given the visitor has no name
    When the greeting is built
    Then the greeting reads "Hello, world!"

  Scenario: A visitor's name is padded with whitespace
    Given the visitor is named "  Zac  "
    When the greeting is built
    Then the greeting reads "Hello, Zac!"
