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
  #
  # gary-web's lines are in the browser console now rather than a server's
  # stdout, which costs more than it sounds: nobody collects a console. What
  # survives is the pairing — an id read off a console still finds its other
  # half in gary-api's log — and that is what these two scenarios protect.

  Scenario: A sign in is one request id in two logs
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    Then I should be on the home page
    And gary-web should have logged the call it made to gary-api
    And gary-api should have logged receiving that call
    And the two lines should carry the same request id

  # Two requests, not one: the page is fetched, and then the page calls
  # gary-api. A header on the first is not carried onto the second, and only
  # the second is what either log records.
  #
  # What this scenario used to say was that gary-web's server minted the id
  # and ignored what the browser offered. There is no server now, so the
  # browser is the source — gary-api records the id it is handed. A forged one
  # can put a misleading line in a log and reach nothing else, which is a cost
  # of having no server rather than an oversight.
  Scenario: An id set on the page request does not become the call's id
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the home page with "x-request-id" set to "pasted-by-hand"
    Then gary-web should have logged the call it made to gary-api
    And no line in either log should have "request_id" set to "pasted-by-hand"
