Feature: Being called from a browser
  As gary-web, running entirely in someone's browser
  I want gary-api to answer calls made from the page
  So that a client with no server of its own is still a first-class client

  # gary-api is deliberately client-agnostic, and a browser is the one client
  # that cannot simply choose to call it: the browser refuses to hand over the
  # answer unless gary-api says the origin is welcome. Which origins those are
  # is a deployment's business, so it is read from the environment rather than
  # being open to everyone.

  Scenario: An origin gary knows is allowed to read the answer
    Given "https://gary-web.fly.dev" is allowed in a browser
    When a page at "https://gary-web.fly.dev" asks what it may send
    Then the answer should be addressed to "https://gary-web.fly.dev"
    And a session token should be allowed through
    # Without this every call is a refused preflight, because a browser will
    # not send a header it has not been told it may.
    And the id that pairs the two logs should be allowed through

  Scenario: An origin gary does not know gets nothing back
    Given "https://gary-web.fly.dev" is allowed in a browser
    When a page at "https://not-gary.example.com" asks what it may send
    Then the answer should be addressed to nobody

  Scenario: A deployment can allow more than one
    Given "https://gary-web.fly.dev" and "http://localhost:3000" are allowed in a browser
    When a page at "http://localhost:3000" asks what it may send
    Then the answer should be addressed to "http://localhost:3000"

  # Signing in is the call that matters: it is a POST carrying JSON, which is
  # exactly the shape a browser will not send without asking first.
  Scenario: The call that starts a session is one a browser may make
    Given "https://gary-web.fly.dev" is allowed in a browser
    When a page at "https://gary-web.fly.dev" asks whether it may sign someone in
    Then the answer should be addressed to "https://gary-web.fly.dev"
    And POST should be allowed through
