Feature: Combat
  As someone whose character is in a fight
  I want the order and the outcomes decided by the rules
  So that a fight is something I play rather than something I am read

  # What prompted this, from a real session: gary ran a whole encounter with
  # bare roll calls. It invented an initiative modifier for each character
  # (+1, +2, +3, +4 — from nowhere; every sheet was straight tens), invented a
  # monster with no hit points anything could track, rolled "mud creature slam
  # vs Gus" with the target's name in the reason field because there was
  # nowhere else to put it, and took the player's turn for them.
  #
  # Every one of those is the failure the engines exist to prevent, and gary
  # is not at fault for any of it: there was no combat, so it improvised one.
  #
  # The rule this whole file is about: ORDER AND OUTCOME ARE THE ENGINE'S.
  # Gary says who is fighting and what they are trying. It never says who goes
  # first, whether a blow lands, or how much it hurt.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"
    And I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    And "Gus" the fighter has dex 16, and is mine
    And "Sara" the cleric has dex 8

  # ----------------------------------------------------------- starting one

  Scenario: Starting a fight rolls initiative for everybody in it
    When I say "it lunges [[fight mud-creature]]"
    Then everybody in the fight should have rolled initiative
    And the order should run from highest to lowest
    And it should be round 1

  # Gary picked the numbers before because nothing else would. It still
  # authors the monster — choosing what you fight is the one genuinely
  # authorial thing in a fight — but from there the monster is a row like any
  # other, and what happens to it is the engine's.
  Scenario: The monster gary brings is a thing the world knows about
    When I say "it lunges [[fight mud-creature]]"
    Then the world should have "mud creature" in the fight
    And "mud creature" should have hit points
    And "mud creature" should not be in the party

  Scenario: Initiative uses each character's own dexterity
    When I say "it lunges [[fight mud-creature]]"
    Then "Gus" should have rolled initiative with a modifier of 3
    And "Sara" should have rolled initiative with a modifier of -1

  Scenario: A fight that is already happening does not start again
    Given I said "it lunges [[fight mud-creature]]"
    When I say "another one [[fight second-creature]]"
    Then the tool should be refused
    And the refusal should say a fight is already happening

  # ------------------------------------------------------------- taking one

  # The whole point of the order being the engine's: gary cannot decide that
  # the monster goes first because it would read better.
  Scenario: Only whoever is up may act
    Given I said "it lunges [[fight mud-creature]]"
    When gary has somebody act out of turn
    Then the tool should be refused
    And the refusal should say whose turn it is

  Scenario: An attack is rolled and graded by the rules
    Given I said "it lunges [[fight mud-creature]]"
    When the one whose turn it is attacks
    Then the attack should have been rolled against the target's armour class
    And gary should have been told what happened

  # Hit or miss is the rules', so a scenario cannot demand one without
  # arranging the dice. What it can demand is that the two agree: damage when
  # it landed, nothing when it did not, and never the other way round.
  Scenario: What an attack costs follows from whether it landed
    Given I said "it lunges [[fight mud-creature]]"
    When the one whose turn it is attacks
    Then the damage should match whether it hit
    And the history should say which turn did it

  Scenario: Ending a turn moves to the next one in the order
    Given I said "it lunges [[fight mud-creature]]"
    When the one whose turn it is ends it
    Then it should be the next one's turn

  Scenario: The order comes round again, and the round goes up
    Given I said "it lunges [[fight mud-creature]]"
    When everybody has had a turn
    Then it should be round 2

  # ---------------------------------------------- whose character this is

  # The thing that was asked for first and is the reason any of this exists:
  # the others are gary's to voice, and the one you play is not. Gary reaching
  # your turn has to stop the turn, not narrate through it.
  Scenario: Gary is told to stop when it is my turn
    Given I said "it lunges [[fight mud-creature]]"
    And the order has reached "Gus"
    When I say "I look around"
    Then gary should have been told to stop and ask me

  Scenario: Gary cannot end my turn for me
    Given I said "it lunges [[fight mud-creature]]"
    And the order has reached "Gus"
    When I say "and then [[endturn]]"
    Then the tool should be refused
    And the refusal should say it is mine to take

  # Directing a companion is not the same as being played for. Gary voices
  # Sara, and "Sara, hold the line" is an instruction gary carries out.
  Scenario: I can tell a companion what to do on their turn
    Given I said "it lunges [[fight mud-creature]]"
    And the order has reached "Sara"
    When I say "Sara, swing at it [[attack Sara mud-creature]]"
    Then the attack should have been made

  # ------------------------------------------------------------- ending one

  Scenario: Gary can call a fight off
    Given I said "it lunges [[fight mud-creature]]"
    When I say "it slides back under [[peace]]"
    Then the fight should be over

  Scenario: Attacking when there is no fight
    When I say "I swing at nothing [[attack Gus Sara]]"
    Then the tool should be refused
    And the refusal should say there is no fight

  # A campaign is told what it is in the middle of, every turn, the same way
  # it is told where the party is — otherwise gary is running a fight from
  # whatever the last few paragraphs implied, which is where drift starts.
  Scenario: What gary is told while a fight is on
    Given I said "it lunges [[fight mud-creature]]"
    When I say "I look around"
    Then gary should have been told the order
    And gary should have been told whose turn it is
    And gary should have been told the round

  # ------------------------------------------------------------ per system

  # The same argument as the four-degree systems and the ability modifiers:
  # what a system does differently, it does differently here too, and nothing
  # between gary and the engine knows the difference.
  Scenario: A system that rolls initiative differently rolls it differently
    Given I started "Salt in the wind" on "pathfinder-2e" running "salt-and-cinder"
    And "Ket" the rogue has dex 16, and is mine
    When I say "it lunges [[fight brine-hound]]"
    Then everybody in the fight should have rolled initiative

  # First edition rolls one d6 per side and moves whole sides at a time,
  # which is a different shape from the flat order everything above assumes —
  # not a different number in the same shape. Refused rather than
  # approximated: a log saying each of them rolled their own initiative would
  # be a record of something that never happened at a first edition table.
  # Same reason its ability modifiers return nothing.
  Scenario: First edition does not do fights yet, and says so
    Given I started "The heath" on "add-1e" running "the-moaning-barrow"
    And "Osric" the fighter has dex 16, and is mine
    When I say "it rears up [[fight barrow-wight]]"
    Then the tool should be refused
    And the refusal should say this system cannot do fights yet

  Scenario: Swinging at somebody who is not in the fight
    Given I said "it lunges [[fight mud-creature]]"
    When I say "at the ghost [[attack Gus ghost]]"
    Then the tool should be refused
    And the refusal should say nobody is called that

  Scenario: Swinging at yourself
    Given I said "it lunges [[fight mud-creature]]"
    When I say "at myself [[attack Gus Gus]]"
    Then the tool should be refused
    And the refusal should say you cannot hit yourself

  # A fight that has been fought is still a fact about the campaign, so what
  # was in it stays on the board after it ends.
  Scenario: What was fought is remembered after the fight
    Given I said "it lunges [[fight mud-creature]]"
    And I said "it slides back under [[peace]]"
    When I say "I look around"
    Then gary should have been told what was fought

  Scenario: Swinging at something already down
    Given I said "it lunges [[fight mud-creature]]"
    And "mud creature" has been knocked down
    When I say "again [[attack Gus mud-creature]]"
    Then the tool should be refused
    And the refusal should say they are already down

  # Two of them, so that finding the second proves the search does not stop
  # at the first — which one monster could never show.
  Scenario: Hurting the second of two things by name
    Given I said "it lunges [[fight mud-creature]]"
    And I said "it slides back under [[peace]]"
    And I said "another one [[fight bog-hound]]"
    When I say "it reels [[damage bog hound 3]]"
    Then "bog hound" should be 3 hit points down on the other side
