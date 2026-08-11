Feature: An answer gary-web cannot read is reported, not a blank page
  As someone using gary
  I want a broken answer from gary-api to say so
  So that a failure looks like a failure rather than an empty screen

  # The trigger is a real failure rather than a debug route: gary-api
  # answering with something that is not JSON — a proxy error page, a
  # truncated body. It arrives as a 200, so nothing about the status says
  # anything is wrong; only parsing it does.
  #
  # This used to be a server crash, caught by Next and logged through
  # onRequestError. gary-web has no server now, so an unhandled parse would
  # throw inside a render and leave a blank page. Handling it where the call
  # is made is what keeps that from happening.

  Scenario: gary-api answers with something that is not JSON
    Given I am signed in as "Ada"
    When I open the home page
    Then I should be signed in as "Ada"
    When gary-api starts answering with something that is not JSON
    And I reload the page
    Then I should be on the sign in page
    And gary-web should have logged a "api.unreadable" line for "/auth/me"
    And that line should name the error type and message
