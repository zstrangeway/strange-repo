Feature: Profile
  As a signed-in user
  I want to read and correct my details
  So that gary shows the right name

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"

  Scenario: Reading my profile
    When I GET "/auth/me"
    Then the response status should be 200
    And the response field "email" should be "ada@example.com"
    And the response field "display_name" should be "Ada Lovelace"
    And the response should carry no token

  Scenario: Reading a profile without a session
    Given I am signed out
    When I GET "/auth/me"
    Then the response status should be 401

  Scenario: Changing my display name
    When I PATCH "/auth/me" with:
      """
      {"display_name": "Ada L"}
      """
    Then the response status should be 200
    And the response field "display_name" should be "Ada L"
    And the user "ada@example.com" should have display name "Ada L"

  Scenario: Changing a display name without a session
    Given I am signed out
    When I PATCH "/auth/me" with:
      """
      {"display_name": "Someone Else"}
      """
    Then the response status should be 401

  Scenario: A display name cannot be blank
    When I PATCH "/auth/me" with:
      """
      {"display_name": "   "}
      """
    Then the response status should be 422
    And the user "ada@example.com" should have display name "Ada Lovelace"

  # The address is whatever the provider that opened the account said. gary
  # never verified it and offers no way to edit it, because editing it would
  # imply it means something.
  Scenario: The address is not mine to change here
    When I PATCH "/auth/me" with:
      """
      {"display_name": "Ada L", "email": "someone@example.com"}
      """
    Then the response status should be 200
    And the response field "email" should be "ada@example.com"
