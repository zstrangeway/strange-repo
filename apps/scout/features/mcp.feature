Feature: scout as an MCP server
  As someone who lives in a Claude Code session
  I want the same three capabilities as tools
  So that I can find a posting, tailor for it and log it without leaving

  # These specs drive a real MCP client over a real stdio pipe to a real
  # scout server process, against a real SQLite file in a scratch directory.
  # Only the model is stubbed. The point is that a stdio server is broken by
  # things no in-process test can see — a stray print, a slow import, a
  # missing entry point — and every one of those is somebody staring at
  # "server disconnected" with nothing to read.
  #
  # The CLI and the server are the same code underneath. The tools are a
  # second surface onto the capability, not a second implementation of it.

  Background:
    Given a scratch scout directory
    And scout's MCP server running over stdio

  # ------------------------------------------------------------ the surface

  Scenario: The three capabilities are there
    When I ask the server what tools it has
    Then the tools should include one for saving a posting
    And the tools should include one for tailoring a resume
    And the tools should include one for logging a status

  # A fourth, read-only: without it a session can save and tailor but cannot
  # see what it saved, so the full flow needs the human to go and read the
  # database.
  Scenario: And one for seeing what I have
    When I ask the server what tools it has
    Then the tools should include one for listing postings

  # And a fifth, for the reason the save tool gave it away: when the company
  # is unknown its reply says to set it — and said so naming a command that
  # only existed on the command line. A tool telling a model to do something
  # it has no tool for is a dead end at the exact moment somebody is trying
  # to finish the flow without leaving the session.
  Scenario: And one for filling in what scout would not guess
    When I ask the server what tools it has
    Then the tools should include one for editing a posting

  Scenario: Every tool says what it needs
    When I ask the server what tools it has
    Then every tool should describe what it does
    And every tool should declare the arguments it takes

  # ------------------------------------------------------------- doing work

  Scenario: Saving a posting through the server
    When I call the save tool with a pasted posting for "Staff Engineer" at "Orrery"
    Then the call should succeed
    And the reply should name the posting's reference
    And the posting should be in the database

  Scenario: Tailoring through the server
    Given a master resume naming "Wilding Labs" and "Thornfield Systems"
    And I have saved a posting for "Staff Engineer" at "Orrery"
    And the model will return a draft drawn only from the master
    When I call the tailor tool for that posting
    Then the call should succeed
    And the reply should say where the resume was written
    And the reply should summarise what changed

  # The grounding check is in the capability, not in the CLI's argument
  # parsing, so it holds on this surface too. A model driving these tools is
  # exactly the situation the check exists for.
  Scenario: A draft that invents something, through the server
    Given a master resume naming "Wilding Labs" and "Thornfield Systems"
    And I have saved a posting for "Staff Engineer" at "Orrery"
    And the model will return a draft claiming "Kubernetes"
    When I call the tailor tool for that posting
    Then the call should report a failure
    And the reply should say "Kubernetes" is not in the master resume
    And no resume file should have been written

  Scenario: Setting the company through the server
    When I call the save tool with a pasted posting naming no company
    Then the reply should say the company is unknown
    And the reply should name a tool I can call to set it
    When I call the edit tool for that posting with company "Orrery"
    Then the call should succeed
    And that posting's company should be "Orrery"

  Scenario: Logging a status through the server
    Given I have saved a posting for "Staff Engineer" at "Orrery"
    When I call the log tool for that posting with "applied" noting "referral from Ada"
    Then the call should succeed
    And that posting's status should be "applied"

  Scenario: The whole flow without leaving the session
    Given a master resume naming "Wilding Labs" and "Thornfield Systems"
    And the model will return a draft drawn only from the master
    When I call the save tool with a pasted posting for "Staff Engineer" at "Orrery"
    And I call the tailor tool for that posting
    And I call the log tool for that posting with "applied" noting "sent the tailored one"
    Then that posting's status should be "applied"
    And a resume should be written for that posting at version 1

  # ------------------------------------------------------- when it goes wrong

  # A tool that raises through the transport takes the session's turn with it.
  # A refusal is a result: the model reads it and can tell the human what
  # happened, or fix the argument and go again.
  Scenario: A refusal comes back as a result, not a crash
    When I call the log tool for a posting that does not exist with "applied"
    Then the call should report a failure
    And the reply should say no such posting
    And the server should still be running

  Scenario: A tool called with arguments missing
    When I call the tailor tool with no posting at all
    Then the call should report a failure
    And the server should still be running

  # ---------------------------------------------------------- the pipe itself

  # stdout is the protocol. One print statement in a startup path and the
  # client's first parse fails, which surfaces to a human as a server that
  # will not connect and no explanation anywhere.
  Scenario: Nothing but protocol on stdout
    When I call the save tool with a pasted posting for "Staff Engineer" at "Orrery"
    Then everything the server wrote to stdout should be protocol frames

  Scenario: Its logs go to stderr
    When I call the save tool with a pasted posting for "Staff Engineer" at "Orrery"
    Then the server's own log lines should have gone to stderr

  # The config block in the README is the thing somebody pastes into Claude
  # Code. If it drifts from what the package actually installs, the first
  # thing anybody does with scout fails.
  Scenario: The README's config block is the one that works
    Given the command in the README's Claude Code config block
    When I start a server with exactly that command
    Then the server should answer what tools it has
