Feature: Signing in and out
  As someone with a Google, Facebook or Apple account
  I want a session that starts when a provider vouches for me
  So that gary knows who I am without ever holding a password of mine

  Scenario: A first sign-in opens an account
    When I sign in at google as "ada@example.com" named "Ada Lovelace"
    Then the response status should be 201
    And I should be signed in

  Scenario: Signing in again returns the same account
    Given an account exists at google for "ada@example.com" named "Ada Lovelace"
    When I sign in at google as "ada@example.com" named "Ada Lovelace"
    Then the response status should be 201
    And the account should be the one for "ada@example.com"

  # The heart of it. gary cannot verify an address, so two providers naming
  # the same one is not evidence of the same person — and treating it as
  # evidence is how an account gets taken over.
  Scenario: The same address at another provider is another account
    Given an account exists at google for "ada@example.com" named "Ada Lovelace"
    When I sign in at facebook as "ada@example.com" named "Ada Lovelace"
    Then the response status should be 201
    And the account should not be the one for "ada@example.com"

  Scenario: Every provider can open an account
    When I sign in at apple as "l9x2@privaterelay.appleid.com" named "Ada"
    Then the response status should be 201
    And I should be signed in

  Scenario: A code the provider will not honour is refused
    When I sign in at google with a code it will not accept
    Then the response status should be 401
    And the response body should be:
      """
      {"detail": "Sign in with Google did not work, try again"}
      """
    And I should not be signed in

  Scenario: A provider gary does not offer is refused
    When I sign in at myspace as "ada@example.com" named "Ada"
    Then the response status should be 400
    And I should not be signed in

  Scenario: Signing out ends this session
    Given I am signed in at google as "ada@example.com" named "Ada"
    When I DELETE "/auth/sessions/current"
    Then the response status should be 204
    And I should not be signed in

  Scenario: Signing out leaves my other devices alone
    Given I am signed in at google as "ada@example.com" named "Ada"
    And I am also signed in on another device
    When I DELETE "/auth/sessions/current"
    Then the response status should be 204
    And the session on the other device should still work

  Scenario: An expired session is not a session
    Given I am signed in at google as "ada@example.com" named "Ada"
    And my session expired an hour ago
    When I GET "/auth/me"
    Then the response status should be 401

  Scenario: A token nobody issued is not a session
    Given I carry a session token that was never issued
    When I GET "/auth/me"
    Then the response status should be 401

  Scenario: Where to sign in is gary's to say, not each client's
    When I ask where to sign in
    Then the response status should be 200
    And the offered ways to sign in should be google, facebook and apple
    And every way to sign in should carry somewhere to go

  Scenario: A deployment can offer fewer
    Given only google and apple are configured
    When I ask where to sign in
    Then the offered ways to sign in should be google and apple
