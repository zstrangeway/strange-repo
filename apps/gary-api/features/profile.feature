Feature: Profile
  As a signed-in user
  I want to read and change my own details
  So that gary shows the right name and I can rotate my password

  Background:
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And the user "ada@example.com" has display name "Ada"

  Scenario: Reading my profile
    Given I am signed in as "ada@example.com" with password "a long enough password"
    When I GET "/auth/me"
    Then the response status should be 200
    And the response field "email" should be "ada@example.com"
    And the response field "display_name" should be "Ada"
    And the response should carry no password

  Scenario: Reading a profile without a session
    When I GET "/auth/me"
    Then the response status should be 401

  Scenario: Changing my display name
    Given I am signed in as "ada@example.com" with password "a long enough password"
    When I PATCH "/auth/me" with:
      """
      {"display_name": "Ada Lovelace"}
      """
    Then the response status should be 200
    And the response field "display_name" should be "Ada Lovelace"
    And the user "ada@example.com" should have display name "Ada Lovelace"

  Scenario: Changing a display name without a session
    When I PATCH "/auth/me" with:
      """
      {"display_name": "Ada Lovelace"}
      """
    Then the response status should be 401
    And the user "ada@example.com" should have display name "Ada"

  Scenario: A display name cannot be blank
    Given I am signed in as "ada@example.com" with password "a long enough password"
    When I PATCH "/auth/me" with:
      """
      {"display_name": "   "}
      """
    Then the response status should be 422
    And the user "ada@example.com" should have display name "Ada"

  Scenario: Changing my password
    Given I am signed in as "ada@example.com" with password "a long enough password"
    When I POST "/auth/me/password" with:
      """
      {
        "current_password": "a long enough password",
        "new_password": "an even better password"
      }
      """
    Then the response status should be 204
    And "ada@example.com" should be able to sign in with "an even better password"
    And "ada@example.com" should not be able to sign in with "a long enough password"

  Scenario: Changing my password needs the current one
    Given I am signed in as "ada@example.com" with password "a long enough password"
    When I POST "/auth/me/password" with:
      """
      {
        "current_password": "the wrong password",
        "new_password": "an even better password"
      }
      """
    Then the response status should be 403
    And "ada@example.com" should be able to sign in with "a long enough password"

  Scenario: The new password must be long enough
    Given I am signed in as "ada@example.com" with password "a long enough password"
    When I POST "/auth/me/password" with:
      """
      {"current_password": "a long enough password", "new_password": "short"}
      """
    Then the response status should be 422
    And "ada@example.com" should be able to sign in with "a long enough password"

  # A password change is what you do when you think someone else has it, so
  # every other session it could have been used on has to go.
  Scenario: Changing my password signs out my other devices
    Given I am signed in as "ada@example.com" with password "a long enough password"
    And I am also signed in on another device
    When I POST "/auth/me/password" with:
      """
      {
        "current_password": "a long enough password",
        "new_password": "an even better password"
      }
      """
    Then the response status should be 204
    And the session on the other device should be refused
    And I should be signed in
