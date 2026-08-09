Feature: Password reset
  As a user who has forgotten my password
  I want a one-time link emailed to me
  So that I can set a new password without help

  Background:
    Given a user exists with email "ada@example.com" and password "a long enough password"

  Scenario: Asking for a reset link
    When I POST "/auth/password-reset" with:
      """
      {"email": "ada@example.com"}
      """
    Then the response status should be 202
    And a password reset email should be sent to "ada@example.com"
    And the email should carry a reset link

  # Same status and body as a known address, and no mail either way that a
  # third party could time — otherwise this endpoint lists who has an account.
  Scenario: Asking for a link for an address with no account
    When I POST "/auth/password-reset" with:
      """
      {"email": "nobody@example.com"}
      """
    Then the response status should be 202
    And no email should be sent

  Scenario: Setting a new password with the link
    Given "ada@example.com" has asked for a reset link
    When I POST "/auth/password-reset/confirm" with the emailed token and:
      """
      {"new_password": "an even better password"}
      """
    Then the response status should be 204
    And "ada@example.com" should be able to sign in with "an even better password"
    And "ada@example.com" should not be able to sign in with "a long enough password"

  Scenario: The link only works once
    Given "ada@example.com" has asked for a reset link
    And the emailed token has already been used to set the password "an even better password"
    When I POST "/auth/password-reset/confirm" with the emailed token and:
      """
      {"new_password": "a third password entirely"}
      """
    Then the response status should be 400
    And "ada@example.com" should be able to sign in with "an even better password"

  Scenario: An expired link is refused
    Given "ada@example.com" has asked for a reset link
    And the emailed token expired an hour ago
    When I POST "/auth/password-reset/confirm" with the emailed token and:
      """
      {"new_password": "an even better password"}
      """
    Then the response status should be 400
    And "ada@example.com" should be able to sign in with "a long enough password"

  Scenario: An invented token is refused
    When I POST "/auth/password-reset/confirm" with a token that was never issued and:
      """
      {"new_password": "an even better password"}
      """
    Then the response status should be 400

  Scenario: The new password must be long enough
    Given "ada@example.com" has asked for a reset link
    When I POST "/auth/password-reset/confirm" with the emailed token and:
      """
      {"new_password": "short"}
      """
    Then the response status should be 422
    And "ada@example.com" should be able to sign in with "a long enough password"

  # Resetting is the recovery path for an account you think is compromised,
  # so it has to end whatever sessions the other party may be holding.
  Scenario: Resetting my password signs out every session
    Given I am signed in as "ada@example.com" with password "a long enough password"
    And "ada@example.com" has asked for a reset link
    When I POST "/auth/password-reset/confirm" with the emailed token and:
      """
      {"new_password": "an even better password"}
      """
    Then the response status should be 204
    And I should not be signed in

  Scenario: Asking again replaces the previous link
    Given "ada@example.com" has asked for a reset link
    And I keep that first token
    When "ada@example.com" asks for a reset link again
    And I POST "/auth/password-reset/confirm" with the first token and:
      """
      {"new_password": "an even better password"}
      """
    Then the response status should be 400
    And "ada@example.com" should be able to sign in with "a long enough password"
