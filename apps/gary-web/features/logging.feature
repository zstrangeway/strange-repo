@fullstack
Feature: One action, one story across both logs
  As an operator of gary
  I want a single thing a person did to be findable in both apps' logs at once
  So that "it failed for Ada at 3pm" is one search rather than two guesses

  # The shape of a gary-web log line is covered by Vitest over src/lib, which
  # is faster and gated at 100%. What no unit test can reach is the thing this
  # feature exists for: that the id gary-web puts on a line is the same id
  # gary-api puts on its own, for the same click. That needs both processes
  # running, so it lives in the full-stack tier with the other four.

  Scenario: A sign up is one request id in two logs
    Given I am signed out
    When I open the sign up page
    And I sign up as "Ada" with email "ada@example.com" and password "a long enough password"
    Then I should be on the home page
    And gary-web should have logged the call it made to gary-api
    And gary-api should have logged receiving that call
    And the two lines should carry the same request id

  # The browser is not a trusted source of trace ids. Whatever it sends, the
  # id on the line is the one gary-web minted.
  Scenario: A request id offered by the browser is not taken on trust
    Given I am signed out
    When I open the home page with "x-request-id" set to "pasted-by-hand"
    Then no gary-web line should have "request_id" set to "pasted-by-hand"

  Scenario: gary-api being down is logged as one object, not a stack trace
    Given I am signed out
    And gary-api has stopped
    When I open the sign in page
    And I sign in with email "ada@example.com" and password "a long enough password"
    Then the page shows "gary is unavailable, try again shortly"
    And gary-web should have logged that at error with "error.type" and "error.message"
    And that line should carry the same request id as the page's own line
