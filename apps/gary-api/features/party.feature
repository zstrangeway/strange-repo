Feature: Who is at the table, and who plays them
  As someone starting a campaign
  I want to say which character is mine and let gary play the rest
  So that I am one person at a table rather than the whole party at once

  # Building the party is its own step now, before play rather than beside it.
  # What forced it: the campaign page loaded saying "gary is setting the
  # scene" while gary was doing nothing of the sort, because there was nobody
  # to set it for. A page that cannot proceed should say what it is waiting
  # for, and the cleanest way to say it is to make the waiting its own screen.
  #
  # And one character is mine. The rest are companions: gary speaks for them,
  # decides what they say and how they take things, and I may tell them what
  # to do. The line is the same one that already runs through gary — the world
  # is gary's and my character's choices are mine — with the companions
  # falling on gary's side of it until I direct them.
  #
  # Combat does not exist yet, so "I control them in combat" is not something
  # these scenarios can assert. What they assert is the part that works
  # without it: a companion does what I tell it, and gary voices it when I do
  # not. When there is a turn order, that convention becomes structure.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"
    And I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"

  Scenario: The character I play
    When I add "Bramble" the rogue as mine
    Then the response status should be 201
    And the party should say "Bramble" is mine

  Scenario: A companion for gary to play
    Given I add "Bramble" the rogue as mine
    When I add "Maud" the cleric as a companion
    Then the response status should be 201
    And the party should say "Maud" is gary's

  Scenario: Reading the party says who plays whom
    Given I add "Bramble" the rogue as mine
    And I add "Maud" the cleric as a companion
    When I read the party
    Then the response status should be 200
    And the party should be "Bramble", "Maud"
    And exactly 1 character should be mine

  # One is the whole idea. Two would put me back to playing the party.
  Scenario: A second character of mine is refused
    Given I add "Bramble" the rogue as mine
    When I add "Ket" the fighter as mine
    Then the response status should be 409
    And the response code should be "already_playing"

  Scenario: Changing my mind about which one is mine
    Given I add "Bramble" the rogue as mine
    And I add "Maud" the cleric as a companion
    When I take over "Maud"
    Then the response status should be 200
    And the party should say "Maud" is mine
    And the party should say "Bramble" is gary's
    And exactly 1 character should be mine

  Scenario: Taking over somebody who is not at this table
    Given I add "Bramble" the rogue as mine
    When I take over somebody who does not exist
    Then the response status should be 404

  Scenario: Somebody else's party
    Given another account has a campaign
    When I take over one of their characters
    Then the response status should be 404

  # ------------------------------------------------- what it takes to play

  # The old refusal was "nobody at the table". This one is narrower and it is
  # the one the party step exists to make impossible: characters, but none of
  # them mine, so nobody for me to be.
  Scenario: A party with nobody of mine in it cannot play
    Given I add "Maud" the cleric as a companion
    When I say "I push open the door"
    Then the response status should be 409
    And the response code should be "no_character"

  Scenario: A party with nobody of mine in it cannot begin either
    Given I add "Maud" the cleric as a companion
    When I ask gary to begin
    Then the response status should be 409
    And the response code should be "no_character"

  Scenario: An empty campaign still says there is nobody at all
    When I say "I push open the door"
    Then the response status should be 409
    And the response code should be "no_party"

  # --------------------------------------------------- what gary is told

  Scenario: Gary is told which character is not its to speak for
    Given I add "Bramble" the rogue as mine
    And I add "Maud" the cleric as a companion
    When I say "I push open the door"
    Then gary should have been told "Bramble" is the player's
    And gary should have been told "Maud" is gary's to play

  Scenario: The world says who plays each of them
    Given I add "Bramble" the rogue as mine
    And I add "Maud" the cleric as a companion
    When I read the world
    Then the response status should be 200
    And the world should say "Bramble" is mine
    And the world should say "Maud" is gary's

  # A companion is gary's to voice and mine to direct, and the engines do not
  # care which — a check on Maud resolves the same either way.
  Scenario: I can tell a companion what to do
    Given I add "Bramble" the rogue as mine
    And I add "Maud" the cleric as a companion
    When I say "Maud, force the door [[check Maud 15 Athletics]]"
    Then the turn should stream to completion
    And the check should have been recorded against 15
