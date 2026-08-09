Feature: Signing in and out
  As a registered user
  I want a session that starts when I sign in and ends when I sign out
  So that gary knows who I am, and stops knowing when I say so

  Background:
    Given a user exists with email "ada@example.com" and password "a long enough password"

  Scenario: Signing in with the right password
    When I POST "/auth/sessions" with:
      """
      {"email": "ada@example.com", "password": "a long enough password"}
      """
    Then the response status should be 201
    And I should be signed in

  Scenario: Signing in is not case sensitive about the email
    When I POST "/auth/sessions" with:
      """
      {"email": "Ada@Example.COM", "password": "a long enough password"}
      """
    Then the response status should be 201
    And I should be signed in

  Scenario: The password is wrong
    When I POST "/auth/sessions" with:
      """
      {"email": "ada@example.com", "password": "the wrong password"}
      """
    Then the response status should be 401
    And the response body should be:
      """
      {"detail": "Invalid email or password"}
      """
    And I should not be signed in

  # Identical status and body to the wrong-password case: telling the two
  # apart would let anyone test which addresses have accounts.
  Scenario: The email address is not registered
    When I POST "/auth/sessions" with:
      """
      {"email": "nobody@example.com", "password": "a long enough password"}
      """
    Then the response status should be 401
    And the response body should be:
      """
      {"detail": "Invalid email or password"}
      """
    And I should not be signed in

  Scenario: Signing out ends the session
    Given I am signed in as "ada@example.com" with password "a long enough password"
    When I DELETE "/auth/sessions/current"
    Then the response status should be 204
    And I should not be signed in

  Scenario: Signing out when I was never signed in
    When I DELETE "/auth/sessions/current"
    Then the response status should be 204

  Scenario: Signing out here leaves my other device signed in
    Given I am signed in as "ada@example.com" with password "a long enough password"
    And I am also signed in on another device
    When I DELETE "/auth/sessions/current"
    Then the response status should be 204
    And the session on the other device should still work

  Scenario: A session that has expired is refused
    Given I am signed in as "ada@example.com" with password "a long enough password"
    And my session expired an hour ago
    When I GET "/auth/me"
    Then the response status should be 401

  Scenario: An invented session token is refused
    Given I carry a session token that was never issued
    When I GET "/auth/me"
    Then the response status should be 401
