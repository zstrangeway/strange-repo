Feature: Campaigns
  As someone who wants to play
  I want to start a campaign on a system and a module
  So that there is a game to bring characters into

  # A campaign is the first thing in gary that belongs to somebody. Everything
  # below it — characters, turns, rolls — hangs off it, and reaching any of
  # them means reaching the campaign first.
  #
  # Somebody else's campaign answers 404 and never 403. A 403 would confirm it
  # exists, and whether a stranger has a campaign is not mine to learn.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"

  Scenario: Starting a campaign
    When I start "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    Then the response status should be 201
    And the response field "name" should be "A Light in the Deep"
    And the response field "system" should be "dnd-5e"
    And the campaign should have no turns yet

  Scenario: Listing my campaigns, newest first
    Given I started "The first one" on "add-1e" running "the-moaning-barrow"
    And I started "The second one" on "dnd-5e" running "the-drowned-belfry"
    When I GET "/campaigns"
    Then the response status should be 200
    And my campaigns should be "The second one", "The first one"

  Scenario: Reading one of my campaigns
    Given I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    When I read that campaign
    Then the response status should be 200
    And the response field "module" should be "the-drowned-belfry"

  Scenario: A campaign needs a name
    When I start "   " on "dnd-5e" running "the-drowned-belfry"
    Then the response status should be 422

  Scenario: A campaign on a system gary does not run
    When I start "A Light in the Deep" on "call-of-cthulhu" running "the-drowned-belfry"
    Then the response status should be 422
    And the response code should be "no_such_system"

  # The pair has to agree. A module that exists, under a system that exists,
  # but not under that one, is the mistake a dropdown makes easy.
  Scenario: A module that belongs to another system
    When I start "A Light in the Deep" on "dnd-5e" running "the-moaning-barrow"
    Then the response status should be 422
    And the response code should be "no_such_module"

  Scenario: Someone else's campaign is not mine to read
    Given another account has a campaign
    When I read their campaign
    Then the response status should be 404

  Scenario: Someone else's campaign is not in my list
    Given another account has a campaign
    When I GET "/campaigns"
    Then the response status should be 200
    And I should have no campaigns

  Scenario: Starting a campaign needs a session
    Given I am signed out
    When I start "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    Then the response status should be 401

  Scenario: Listing campaigns needs a session
    Given I am signed out
    When I GET "/campaigns"
    Then the response status should be 401
