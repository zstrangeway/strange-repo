Feature: A server crash is logged, not only reported
  As an operator of gary
  I want gary-web's own crashes in the same log as everything else it writes
  So that the log and Sentry cannot disagree about whether a request failed

  # Sentry is where these get triaged, but the Fly log is where every other
  # line this app writes lives. An error in one and not the other leaves two
  # accounts of the same request that do not match.
  #
  # The trigger is a real failure rather than a debug route: gary-api
  # answering with something that is not JSON — a proxy error page, a
  # truncated body. callApi parses it, the parse throws inside a Server
  # Component, and Next hands that to onRequestError.

  Scenario: gary-api answers with something that is not JSON
    Given I am signed in as "Ada"
    When I open the home page
    Then the page shows "Welcome Home, Ada"
    When gary-api starts answering with something that is not JSON
    And I reload the page
    Then gary-web should have logged a "server.error" line for "/"
    And that line should name the error type and message
