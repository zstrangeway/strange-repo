Feature: The catalogue
  As someone deciding what to play
  I want to see the systems and modules gary can run
  So that starting a campaign is a choice rather than a guess

  # The catalogue ships with gary rather than belonging to anyone, so it lives
  # in code and not in a table. A table would need a data migration to reach
  # production — seed refuses to run against anything but a local database —
  # and retiring a system would need another one. Adding a system is a code
  # change and a line in this file.
  #
  # The systems are named because naming a ruleset is not reproducing it: gary
  # runs a game in the manner of an edition, and the modules are gary's own.

  Scenario: The systems gary can run
    When I GET "/catalogue"
    Then the response status should be 200
    And the systems offered should be dnd-5e, dnd-3-5e, add-1e, pathfinder-2e
    And every system should carry a name and a blurb

  Scenario: What a system has to play
    When I GET "/catalogue/dnd-5e"
    Then the response status should be 200
    And the response field "name" should be "Dungeons & Dragons 5th Edition"
    And "the-drowned-belfry" should be among its modules
    And every module should carry a title and a premise

  Scenario: A system gary does not run
    When I GET "/catalogue/call-of-cthulhu"
    Then the response status should be 404
    And the response code should be "no_such_system"

  # Every system has something to play. A system offered with an empty list is
  # a dead end somebody only finds after choosing it.
  Scenario: No system is offered with nothing to run
    When I GET "/catalogue"
    Then every system should have at least one module

  # A menu, not somebody's account. What gary can play should not need an
  # account to find out — it is the thing that decides whether to make one.
  Scenario: The catalogue needs no session
    Given I am signed out
    When I GET "/catalogue"
    Then the response status should be 200
