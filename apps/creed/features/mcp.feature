Feature: creed as an MCP server
  As someone who lives in a Claude Code session
  I want the rules as tools
  So that a model answering a rules question is reading the export, not its training data

  # Same approach as scout's MCP specs, for the same reason: these drive a
  # real MCP client over a real stdio pipe to a real creed process against a
  # real SQLite file. A stdio server is broken by things no in-process test
  # can see — a stray print, a slow import, a missing entry point — and every
  # one of those reaches a human as "server disconnected" with nothing to
  # read.
  #
  # The CLI and the server are the same code underneath. The tools are a
  # second surface onto the capability, not a second implementation.

  Background:
    Given a scratch creed directory
    And creed has a complete sync
    And creed's MCP server running over stdio

  # ------------------------------------------------------------ the surface

  Scenario: The lookup tools are there
    When I ask the server what tools it has
    Then the tools should include one for searching datasheets
    And the tools should include one for getting a datasheet whole
    And the tools should include one for finding stratagems
    And the tools should include one for listing factions

  # Without this a model has no way to tell a human how current its answer
  # is, and "never stale" becomes a claim nobody can check from the outside.
  Scenario: And one for asking how fresh the data is
    When I ask the server what tools it has
    Then the tools should include one for reporting data freshness
    And that tool should report the export's update timestamp
    And that tool should report when creed last checked

  Scenario: Every tool says what it needs
    When I ask the server what tools it has
    Then every tool should describe what it does
    And every tool should declare the arguments it takes

  # ---------------------------------------------------------- doing work

  Scenario: Looking up a datasheet through the server
    When I call the datasheet tool for "Custodian Guard"
    Then the call should succeed
    And the reply should carry its statline and weapons
    And the reply should carry the export's update timestamp

  Scenario: Searching through the server
    When I call the search tool for "contemptor"
    Then the call should succeed
    And the reply should include "Venerable Contemptor Dreadnought"

  Scenario: Finding a stratagem through the server
    When I call the stratagem tool for my own turn in the Shooting phase
    Then the call should succeed
    And every stratagem in the reply should match both

  # A datasheet is a lot of text and a search can match many. A reply that
  # fills a model's context with fifty full datasheets has answered nothing.
  Scenario: A search that matches a great many
    When I call the search tool for something that matches very many
    Then the reply should be capped at a readable number
    And the reply should say how many there were in total
    And the reply should say how to narrow it

  # ------------------------------------------------------- when it goes wrong

  Scenario: A refusal comes back as a result, not a crash
    When I call the datasheet tool for a unit that does not exist
    Then the call should report a failure
    And the reply should say nothing matched
    And the server should still be running

  Scenario: A tool called with arguments missing
    When I call the datasheet tool with no unit at all
    Then the call should report a failure
    And the server should still be running

  # Syncing is 8.3MB over nineteen requests. Doing it inside a tool call
  # blocks the model's turn on a download; failing to do it at all is how the
  # data goes stale. So it happens around the call, and the call says what it
  # is reading.
  Scenario: A sync landing does not interrupt a call in flight
    Given the export has been updated since creed synced
    When I call the datasheet tool for "Custodian Guard"
    Then the call should succeed
    And the reply should say which sync it was answering from

  # ---------------------------------------------------------- the pipe itself

  Scenario: Nothing but protocol on stdout
    When I call the datasheet tool for "Custodian Guard"
    Then everything the server wrote to stdout should be protocol frames

  Scenario: Its logs go to stderr
    When I call the datasheet tool for "Custodian Guard"
    Then the server's own log lines should have gone to stderr

  # Syncing writes progress somewhere. If that somewhere is stdout, the first
  # sync breaks the protocol — and it is the one that always runs.
  Scenario: Syncing says what it did, on stderr
    Given creed has never synced
    When the server starts and syncs
    Then the sync's progress should have gone to stderr
    And the sync should report how many rows it loaded

  Scenario: The README's config block is the one that works
    Given the command in the README's Claude Code config block
    When I start a server with exactly that command
    Then the server should answer what tools it has
