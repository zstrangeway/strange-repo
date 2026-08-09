Feature: Email verification
  As an operator of gary
  I want new accounts to confirm their address
  So that I know the address on an account can actually receive mail

  # Two decisions are baked into these scenarios. Say if either is wrong.
  #
  # An unverified user can still sign in and use gary. Blocking them would
  # mean a mail outage locks out everyone who signed up during it, and gary's
  # mail has already proven able to fail quietly.
  #
  # Accounts that existed before this feature are treated as verified. The
  # alternative is that deploying this silently un-verifies the people
  # already using gary.

  Scenario: Signing up sends a verification link
    When I POST "/auth/register" with:
      """
      {
        "email": "ada@example.com",
        "password": "a long enough password",
        "display_name": "Ada"
      }
      """
    Then the response status should be 201
    And a verification email should be sent to "ada@example.com"
    And the email should carry a verification link

  Scenario: A new account starts unverified
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And I am signed in as "ada@example.com" with password "a long enough password"
    When I GET "/auth/me"
    Then the response status should be 200
    And the response field "email_verified" should be "false"

  Scenario: Following the link verifies the account
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And I am signed in as "ada@example.com" with password "a long enough password"
    When I POST "/auth/verify-email" with the emailed token
    Then the response status should be 204
    And "ada@example.com" should be verified

  # Verifying is not signing in. Doing it from a phone while signed in on a
  # laptop must not disturb either session.
  # A confirmation to the address itself, so someone who did not expect it
  # learns their address was attached to a gary account.
  Scenario: Verifying confirms by email
    Given a user exists with email "ada@example.com" and password "a long enough password"
    When I POST "/auth/verify-email" with the emailed token
    Then the response status should be 204
    And a "verification complete" email should be sent to "ada@example.com"

  Scenario: A refused link confirms nothing
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And the emailed verification token expired a day ago
    When I POST "/auth/verify-email" with the emailed token
    Then the response status should be 400
    And no "verification complete" email should be sent

  # The confirmation is a courtesy after the fact. Failing the request when
  # it cannot go out would report a verification that did happen as though
  # it had not.
  Scenario: Verifying still works when the mail provider is down
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And the mail provider refuses everything
    When I POST "/auth/verify-email" with the emailed token
    Then the response status should be 204
    And "ada@example.com" should be verified

  Scenario: Verifying leaves my sessions alone
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And I am signed in as "ada@example.com" with password "a long enough password"
    When I POST "/auth/verify-email" with the emailed token
    Then the response status should be 204
    And I should be signed in

  Scenario: A link works without being signed in
    Given a user exists with email "ada@example.com" and password "a long enough password"
    When I POST "/auth/verify-email" with the emailed token
    Then the response status should be 204
    And "ada@example.com" should be verified

  Scenario: The link only works once
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And the emailed verification token has already been used
    When I POST "/auth/verify-email" with the emailed token
    Then the response status should be 400

  Scenario: An expired link is refused
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And the emailed verification token expired a day ago
    When I POST "/auth/verify-email" with the emailed token
    Then the response status should be 400
    And "ada@example.com" should not be verified

  Scenario: An invented token is refused
    When I POST "/auth/verify-email" with a verification token that was never issued
    Then the response status should be 400

  Scenario: Asking for another link
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And I am signed in as "ada@example.com" with password "a long enough password"
    When I POST "/auth/verify-email/resend"
    Then the response status should be 202
    And a verification email should be sent to "ada@example.com"

  Scenario: A new link supersedes the previous one
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And I am signed in as "ada@example.com" with password "a long enough password"
    And I keep that first verification token
    When I POST "/auth/verify-email/resend"
    And I POST "/auth/verify-email" with the first verification token
    Then the response status should be 400
    And "ada@example.com" should not be verified

  Scenario: Asking for a link without a session
    When I POST "/auth/verify-email/resend"
    Then the response status should be 401

  Scenario: Asking again once already verified
    Given a user exists with email "ada@example.com" and password "a long enough password"
    And I am signed in as "ada@example.com" with password "a long enough password"
    And "ada@example.com" has verified their address
    When I POST "/auth/verify-email/resend"
    Then the response status should be 202
    And no email should be sent

  # Registration must not hinge on the mail provider. Losing the account
  # because the email could not go out is worse than an unverified account
  # and a resend button.
  Scenario: Signing up when the mail provider is down
    Given the mail provider refuses everything
    When I POST "/auth/register" with:
      """
      {
        "email": "ada@example.com",
        "password": "a long enough password",
        "display_name": "Ada"
      }
      """
    Then the response status should be 201
    And I should be signed in

  Scenario: An unverified account can still sign in
    Given a user exists with email "ada@example.com" and password "a long enough password"
    When I POST "/auth/sessions" with:
      """
      {"email": "ada@example.com", "password": "a long enough password"}
      """
    Then the response status should be 201
    And I should be signed in
