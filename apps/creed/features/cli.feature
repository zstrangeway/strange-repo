Feature: creed on the command line
  As someone with a terminal already open
  I want the same capabilities without a model in the loop
  So that syncing, checking a list and reading a datasheet are things I can just do

  # Same shape as scout: the CLI and the MCP server are two surfaces onto one
  # set of capabilities, not two implementations. Anything the server can do,
  # this can do, and the sync in particular needs to be runnable by hand —
  # it is the first thing to suspect when an answer looks out of date.

  Background:
    Given a scratch creed directory

  Scenario: Syncing by hand
    Given the export is available
    When I run the sync
    Then creed should say how many rows it loaded
    And creed should say what the export's update timestamp is

  # A sync that prints nothing and exits 0 is indistinguishable from a sync
  # that did nothing, which is the failure that wastes an afternoon.
  Scenario: A sync with nothing to do says so
    Given creed synced at the export's current timestamp
    When I run the sync
    Then creed should say the data was already current
    And creed should say when it was last updated

  Scenario: Asking how fresh the data is
    Given creed has a complete sync
    When I ask for the data's status
    Then creed should say the export's update timestamp
    And creed should say when it last checked
    And creed should say how many rows it holds

  Scenario: Looking up a datasheet
    Given creed has a complete sync
    When I look up "Testudo Guard" on the command line
    Then I should get its statline, weapons and abilities

  Scenario: Building a list
    Given creed has a complete sync
    When I start a list, add two units and check it
    Then I should get the total and the check's report

  Scenario: A command that needs data before there is any
    Given creed has never synced
    When I look up "Testudo Guard" on the command line
    Then creed should say to sync first
    And creed should exit non-zero

  Scenario: Every command says what it did
    When I run any command that changes something
    Then creed should say what changed
