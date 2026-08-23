Feature: Advancement
  As someone playing a character over a long campaign
  I want what we survive to make us better at surviving
  So that a campaign is something we come out of changed

  # `level` has been on the sheet since characters existed. It is accepted at
  # creation, folded into the world, and stated to gary in the briefing every
  # single turn — and nothing has ever written it again. `play.py:690` is the
  # only assignment in the codebase. So a party can play fifty scenes, win
  # every fight, and end exactly as strong as they began, while gary is told
  # "level 1 rogue" for the fiftieth time.
  #
  # That is the largest gap between what this app says it is — "play a
  # tabletop campaign" — and what it does.
  #
  # THE MODEL AWARDS EXPERIENCE. IT NEVER AWARDS A LEVEL. This is the same
  # split as everywhere else: gary says what was overcome and what that was
  # worth, exactly as it already says how much damage something did. What
  # that experience adds up to, when it crosses a threshold, and what a level
  # is worth are rules, and rules live in the system.
  #
  # Three things below are decisions rather than description, and are the
  # parts worth arguing about before any of this is built:
  #
  #   1. Gary names the number. The precedent is `damage` — gary already says
  #      "6" and the engine applies it. The counter-argument is that damage is
  #      bounded by a fight and experience is bounded by nothing, so a model
  #      having a strange turn could hand out 10,000 and jump four levels. So
  #      the system bounds a single award (see "no award is unbounded").
  #   2. An award and a level are two events, not one. Gary's award is what it
  #      proposed; the level is what the engine did about it. Folding them
  #      together would put the engine's dice inside gary's event.
  #   3. Level as created is the sheet, and the current level is a fold — the
  #      same shape as max_hp and current hit points. A character made at
  #      level 3 starts on whatever experience level 3 costs, so "made at 3"
  #      and "earned their way to 3" are the same character afterwards.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"
    And I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    And I add "Bramble" the rogue

  # ------------------------------------------------- the table is the system's

  # The whole argument for a system package rather than a paragraph in a
  # prompt, one more time: these tables genuinely differ, and a single global
  # one would be third edition quietly running everybody's game.
  Scenario: A system says what a level costs
    When I read the system "dnd-5e"
    Then level 2 should cost 300 experience
    And level 5 should cost 6500 experience

  Scenario: Another system prices it differently
    When I read the system "dnd-3-5e"
    Then level 2 should cost 1000 experience

  # First edition does not have one table, it has one per class: a fighter
  # reaches second level at 2,000 and a magic-user at 2,500, and they keep
  # diverging all the way up. Lending them a shared curve would be quietly
  # running third edition, which `modifier` already declines to do one method
  # away — and typing eleven tables in from half-memory would be worse,
  # because wrong numbers look exactly like right ones. So it refuses, the way
  # it refuses fights.
  Scenario: First edition refuses to price a level at all
    When I read the system "add-1e"
    Then it should say it cannot price a level

  # What a card shows when there is no next number to reach. The same answer
  # covers somebody at the top of a system that does price levels, because a
  # client has the same thing to say about both.
  Scenario: A world it cannot price offers no next level
    Given I started "The barrow" on "add-1e" running "the-moaning-barrow"
    And I add "Rook" the fighter
    When I read the world
    Then "Rook" should have no next level to reach

  Scenario: A campaign it cannot price refuses the award
    Given I started "The barrow" on "add-1e" running "the-moaning-barrow"
    And I add "Rook" the fighter
    When I say "well fought [[award Rook 300 the barrow]]"
    Then the tool should be refused
    And the refusal should say first edition prices a level per class

  Scenario: A system says where advancement stops
    When I read the system "dnd-5e"
    Then it should advance no further than level 20

  # ------------------------------------------------------- gary awards it

  Scenario: Gary awards experience for something overcome
    When I say "it stops moving [[award Bramble 300 the mud creature]]"
    Then the turn should stream to completion
    And "Bramble" should have 300 experience
    And the award should say it was for "the mud creature"

  # The same argument as a check taking a list: one hazard survived by four
  # people is one thing that happened, and awarding it one at a time costs a
  # round trip each and reaches the round cap describing a single moment.
  Scenario: A whole party is awarded together
    Given I add "Sara" the cleric
    When I say "the belfry is quiet [[award Bramble,Sara 300 the mud creature]]"
    Then "Bramble" should have 300 experience
    And "Sara" should have 300 experience
    And it should have taken one award to do it

  # Named for the same reason a roll carries whose it is and what it was
  # against: "why is Bramble level 4" should have an answer that is a list of
  # things that happened rather than a number somebody arrived at.
  Scenario: Experience is in the history with what it was for
    When I say "it stops moving [[award Bramble 300 the mud creature]]"
    Then the history should hold an award of 300 to "Bramble"
    And it should say what it was for

  # ------------------------------------------------ the engine levels them

  Scenario: Crossing a threshold is a level
    When I say "it stops moving [[award Bramble 300 the mud creature]]"
    Then "Bramble" should be level 2

  Scenario: Not crossing one is not
    When I say "it stops moving [[award Bramble 299 the mud creature]]"
    Then "Bramble" should be level 1
    And "Bramble" should have 299 experience

  # Gary proposed the award. The level is the engine's answer to it, and it is
  # written down separately so the log says who did which.
  Scenario: The level is the engine's event, not gary's
    When I say "it stops moving [[award Bramble 300 the mud creature]]"
    Then the history should hold a level for "Bramble"
    And the level should not be something gary asked for

  # "Gary may not hand out a level" is not a refusal anybody can reach from
  # here, because there is no tool that would express it. That is the whole
  # guarantee, and it is guarded where it can be — tests/test_pluggable.py
  # fails the build if a tool ever appears that writes a level.

  # The other half of the bound: a dungeon worth three levels arrives as three
  # awards rather than one, and the log says so line by line.
  Scenario: One award is worth at most one level
    When I say "it stops moving [[award Bramble 300 the mud creature]]"
    And I say "and the nest behind it [[award Bramble 300 the nest]]"
    Then "Bramble" should be level 2
    And "Bramble" should have 600 experience

  # The guard on decision 1. A model having a strange turn should not be able
  # to take a character from 1 to 9 in a sentence; what it can do is advance
  # them and be seen doing it. The bound is the system's, because "what a
  # level costs" is the only sensible thing to measure an award against.
  Scenario: No award is unbounded
    When I say "you are chosen [[award Bramble 999999 the prophecy]]"
    Then the tool should be refused
    And the refusal should say the award is larger than this system allows

  # -------------------------------------------------------- hit points

  # The dice are the engine's here for exactly the reason they are everywhere
  # else, and the number is written into the event rather than recomputed on
  # read — a fold that rolls dice would give a different answer every time the
  # log was replayed.
  Scenario: A level brings hit points, rolled by the engine
    When I say "it stops moving [[award Bramble 300 the mud creature]]"
    Then "Bramble" should have more maximum hit points than they started with
    And the level should record what was gained

  Scenario: What a level is worth is the class's hit die
    Given I add "Gus" the fighter
    When I say "the belfry is quiet [[award Bramble,Gus 300 the mud creature]]"
    Then what "Gus" gained should come off a fighter's hit die
    And what "Bramble" gained should come off a rogue's hit die

  Scenario: A level raises the maximum and what you are on together
    Given "Bramble" takes 5 damage
    When I say "it stops moving [[award Bramble 300 the mud creature]]"
    Then "Bramble" should still be 5 below their maximum

  # ---------------------------------------------------------- refusals

  # Half an award applied is worse than none: it says two of them were there
  # for something all four survived.
  Scenario: A name nobody at the table has refuses the whole award
    Given I add "Sara" the cleric
    When I say "well done [[award Bramble,Nobody 300 the mud creature]]"
    Then the tool should be refused
    And "Bramble" should have no experience

  Scenario: Experience cannot be taken away
    When I say "you disappoint me [[award Bramble -100 failing]]"
    Then the tool should be refused

  Scenario: An award of nothing is not an award
    When I say "nothing happened [[award Bramble 0 standing about]]"
    Then the tool should be refused

  # ---------------------------------------------- it is the log, not a column

  # The same property hit points have, and the reason there is no snapshot
  # column: what somebody is now is what happened to them, in order.
  Scenario: Advancement survives a scene boundary
    When I say "it stops moving [[award Bramble 300 the mud creature]]"
    And I say "we press on [[scene The stair below]]"
    Then "Bramble" should still be level 2

  Scenario: A character made partway up starts where that level starts
    Given I add "Vale" the wizard at level 3
    Then "Vale" should have 900 experience
    When I say "well fought [[award Vale 1 a rat]]"
    Then "Vale" should be level 3

  # Gary is told this every turn for the same reason it is told the party's
  # hit points: it cannot narrate somebody being on the edge of something it
  # does not know about.
  Scenario: Gary is told how far along everybody is
    When I say "how are we doing"
    Then gary should have been told "Bramble" is level 1
    And gary should have been told how much experience "Bramble" has
