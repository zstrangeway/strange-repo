Feature: Registration
  As a visitor
  I want to create an account with my email address and a password
  So that I can sign in to gary

  Scenario: Creating an account
    When I POST "/auth/register" with:
      """
      {
        "email": "ada@example.com",
        "password": "a long enough password",
        "display_name": "Ada"
      }
      """
    Then the response status should be 201
    And the response field "email" should be "ada@example.com"
    And the response field "display_name" should be "Ada"
    And the response should carry no password
    And I should be signed in

  Scenario: The email address is already registered
    Given a user exists with email "ada@example.com" and password "a long enough password"
    When I POST "/auth/register" with:
      """
      {
        "email": "ada@example.com",
        "password": "a different long password",
        "display_name": "Not Ada"
      }
      """
    Then the response status should be 409
    And I should not be signed in

  Scenario: Email addresses are matched regardless of case
    Given a user exists with email "ada@example.com" and password "a long enough password"
    When I POST "/auth/register" with:
      """
      {
        "email": "Ada@Example.COM",
        "password": "a different long password",
        "display_name": "Ada"
      }
      """
    Then the response status should be 409

  Scenario: The email address is not an address
    When I POST "/auth/register" with:
      """
      {
        "email": "not-an-address",
        "password": "a long enough password",
        "display_name": "Ada"
      }
      """
    Then the response status should be 422

  Scenario: The password is too short
    When I POST "/auth/register" with:
      """
      {
        "email": "ada@example.com",
        "password": "short",
        "display_name": "Ada"
      }
      """
    Then the response status should be 422
    And no user should exist with email "ada@example.com"

  Scenario: A display name is required
    When I POST "/auth/register" with:
      """
      {
        "email": "ada@example.com",
        "password": "a long enough password"
      }
      """
    Then the response status should be 422

  Scenario: Passwords are never stored in the clear
    Given a user exists with email "ada@example.com" and password "a long enough password"
    Then the stored password for "ada@example.com" should not be "a long enough password"
    And the stored password for "ada@example.com" should verify "a long enough password"
    And the stored password for "ada@example.com" should reject "a long enough passworD"
