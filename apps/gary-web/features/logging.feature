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

  Scenario: A sign in is one request id in two logs
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    Then I should be on the home page
    And gary-web should have logged the call it made to gary-api
    And gary-api should have logged receiving that call
    And the two lines should carry the same request id

  # The browser is not a trusted source of trace ids. Whatever it sends, the
  # id on the line is the one gary-web minted.
  Scenario: A request id offered by the browser is not taken on trust
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the home page with "x-request-id" set to "pasted-by-hand"
    Then gary-web should have logged the call it made to gary-api
    And no line in either log should have "request_id" set to "pasted-by-hand"
