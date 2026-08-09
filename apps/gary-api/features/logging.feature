Feature: Structured logs
  As an operator of gary
  I want every line gary-api writes to be one machine-readable object
  So that I can search and filter the logs, and follow a single request
  through them

  # These drive the real app through the real logging configuration and read
  # what actually lands on the log stream. Asserting against the formatter in
  # isolation would stay green while uvicorn's own records — most of a real
  # log — went out in some other shape entirely.

  Scenario: Every line is one JSON object
    When I GET "/health"
    Then every logged line should be a single JSON object
    And every line should carry "timestamp", "level", "logger", "message" and "app"
    And every line should have "app" set to "gary-api"

  Scenario: Levels are names, and timestamps are UTC
    When something logs "cache warmed" at warning
    Then the line for "cache warmed" should have "level" set to "warning"
    And the line for "cache warmed" should have a "timestamp" in UTC ISO-8601 with milliseconds

  Scenario: Fields given at the call site become fields in the object
    When something logs "mail sent" with provider "resend" and attempts 2
    Then the line for "mail sent" should have "provider" set to "resend"
    And the line for "mail sent" should have "attempts" set to the number 2

  # Otherwise a caller passing level="urgent" quietly rewrites the field the
  # log search filters on, and the line lies about itself.
  Scenario: A call-site field cannot overwrite one of the standard fields
    When something logs "odd" with level "urgent"
    Then the line for "odd" should have "level" set to "info"
    And the line for "odd" should have "level_" set to "urgent"

  # A log call is not worth an outage. Anything json cannot serialise is
  # rendered rather than raising inside the handler.
  Scenario: A value JSON cannot represent is rendered, not dropped
    When something logs "saved" with a field that JSON cannot serialise
    Then the line for "saved" should still be a single JSON object
    And the line for "saved" should describe that field as text

  Scenario: A failure carries its exception in the same object
    When something logs a failure with a ValueError saying "no such account"
    Then that line should have "error.type" set to "ValueError"
    And that line should have "error.message" set to "no such account"
    And that line should have an "error.stack" mentioning the raising function
    And that line should not be followed by a bare traceback

  Scenario: LOG_LEVEL sets the floor
    Given LOG_LEVEL is "WARNING"
    When something logs "chatty" at info
    Then nothing should have been logged for "chatty"

  Scenario: Records from libraries are formatted the same way
    When a library logger named "sqlalchemy.engine" logs "SELECT 1"
    Then the line for "SELECT 1" should be a single JSON object
    And the line for "SELECT 1" should have "logger" set to "sqlalchemy.engine"

  Scenario: A request is given an id, and told what it was
    When I GET "/health"
    Then the response should carry an "x-request-id" header
    And every line logged while handling that request should have that same "request_id"

  # So a caller that already has a trace can hand it in and see it again on
  # both sides, rather than the two logs each inventing their own id.
  Scenario: An inbound request id is kept, not replaced
    When I GET "/health" with "x-request-id" set to "abc-123"
    Then the response should carry an "x-request-id" header set to "abc-123"
    And every line logged while handling that request should have "request_id" set to "abc-123"

  Scenario: Concurrent requests do not share an id
    When I GET "/health" twice at the same time
    Then the two responses should carry different "x-request-id" headers
    And no logged line should carry both request ids

  Scenario: Lines logged outside a request have no request id
    When something logs "starting up" outside any request
    Then the line for "starting up" should have no "request_id"

  Scenario: Every request is summarised on one line
    When I GET "/health"
    Then there should be one "http.request" line
    And it should have "method" set to "GET"
    And it should have "path" set to "/health"
    And it should have "status" set to the number 200
    And it should have a "duration_ms" that is a number

  # The end-to-end suite reads the reset link out of this app's own output.
  # JSON escaping the body must not put the link out of its reach.
  Scenario: The reset link the console mailer logs survives being JSON
    Given a user exists with email "ada@example.com" and password "a long enough password"
    When I POST "/auth/password-reset" with:
      """
      {"email": "ada@example.com"}
      """
    Then a logged line should contain a reset link with a readable token
