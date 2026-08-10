Feature: Connected accounts
  As someone who signs in with a provider
  I want to connect the others to the same account
  So that clicking the wrong button does not strand me in an empty one

  # Connecting is done from inside a signed-in session on purpose. Being
  # already signed in is what proves the same person holds both, which is
  # exactly what two matching email addresses do not.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"

  Scenario: What opened the account is connected to it
    When I GET "/auth/me/identities"
    Then the response status should be 200
    And google should be connected
    And facebook should not be connected

  Scenario: Connecting a second provider
    When I connect facebook as "ada@example.com" named "Ada Lovelace"
    Then the response status should be 201
    And facebook should be connected
    And google should be connected

  Scenario: Either provider then reaches the same account
    Given I connect facebook as "ada@example.com" named "Ada Lovelace"
    When I sign in at facebook as "ada@example.com" named "Ada Lovelace"
    Then the account should be the one for "ada@example.com"

  # The address matching is not what makes connecting safe, so it is not
  # what makes this unsafe either: that identity is spoken for.
  Scenario: A provider already held by another account is refused
    Given an account exists at facebook for "someone@example.com" named "Someone"
    When I connect facebook as "someone@example.com" named "Someone"
    Then the response status should be 409
    And the response body should be:
      """
      {"detail": "That Facebook account is already connected to another gary account"}
      """
    And facebook should not be connected

  Scenario: Connecting what is already mine changes nothing
    When I connect google as "ada@example.com" named "Ada Lovelace"
    Then the response status should be 201
    And google should be connected

  Scenario: My only way in cannot be disconnected
    When I disconnect google
    Then the response status should be 409
    And the response body should be:
      """
      {"detail": "That is your only way to sign in"}
      """
    And google should be connected

  Scenario: Disconnecting one of two leaves the other
    Given I connect facebook as "ada@example.com" named "Ada Lovelace"
    When I disconnect google
    Then the response status should be 204
    And google should not be connected
    And facebook should be connected

  Scenario: Disconnecting something that was never connected
    When I disconnect apple
    Then the response status should be 404

  Scenario: Each provider's own address is held against it
    Given I connect apple as "l9x2@privaterelay.appleid.com" named "Ada"
    Then the address held for google should be "ada@example.com"
    And the address held for apple should be "l9x2@privaterelay.appleid.com"

  Scenario: Connecting needs a session
    Given I am signed out
    When I connect facebook as "ada@example.com" named "Ada Lovelace"
    Then the response status should be 401
