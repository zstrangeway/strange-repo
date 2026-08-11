Feature: What a roll says
  As someone reading a transcript
  I want a roll to say who it was for and what it was against
  So that a number in the middle of a story means something

  # Seven rolls landed in one turn and not one of them said whose neck was
  # out. Gary worked around it the only way it could — by writing the name
  # into the reason, "John falling damage" — which puts a mechanical fact in
  # a free-text field where nothing can check it, nothing can render it, and
  # a system that wanted to know whose save it was has to read English.
  #
  # A check already carries a character as far as the engine, because the
  # rules need one to grade against. It is thrown away immediately: the
  # `rolls` table has no column for it, so the name is gone the moment the
  # stream closes and a reloaded transcript is back to bare numbers.

  # Scores stated here rather than per scenario, because half this file is
  # about what a sheet is worth and the other half would otherwise be read as
  # if everybody were average.
  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"
    And I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    And "Bramble" the rogue has dex 8, and is mine
    And "John" the fighter has dex 16

  Scenario: A check says who it was for
    When I say "we cross the planks [[check John 12 avoid collapse]]"
    Then the roll should have been made for "John"

  # One hazard, one difficulty, everybody exposed to it — which is one thing
  # happening, not four. Modelling it as four calls made gary take four
  # round trips to describe one moment, and a turn only gets eight before the
  # loop gives up. A party of four crossing rotten planks reached the wall on
  # its own.
  #
  # Still one roll each, stored separately with its own name and its own
  # modifier. What changes is how many times gary has to ask.
  Scenario: One check covers everybody exposed to the same thing
    When I say "the planks give [[check Bramble,John 12 avoid collapse]]"
    Then there should be 2 rolls
    And the roll should have been made for "John"
    And the roll should have been made for "Bramble"
    And gary should have been told both results

  # All or nothing. Half a check applied is worse than none: the fiction says
  # the party crossed together and the log would say two of them did.
  Scenario: A check naming somebody who is not there is refused whole
    When I say "the planks give [[check Bramble,Mortisha 12 avoid collapse]]"
    Then the roll should be refused
    And the refusal should name "Mortisha"
    And there should be no rolls

  # The half that is missing today. What the stream carries and what the
  # transcript carries have to be the same thing, or a reload quietly loses
  # what the table was reading a moment ago.
  Scenario: Who it was for survives a reload
    Given I said "we cross the planks [[check John 12 avoid collapse]]"
    When I read the transcript
    Then the roll should still say it was for "John"

  # A bare roll cannot name anybody at all today, which is why gary writes
  # "John falling damage" into the reason. Given somewhere to put the name,
  # it has no reason to smuggle it.
  Scenario: A bare roll can name somebody too
    When I say "the timbers give [[roll John 1d6 falling damage]]"
    Then the roll should have been made for "John"

  Scenario: A roll for nobody in particular stays that way
    When I say "how sound are the timbers [[roll 1d20 the timbers]]"
    Then the roll should have been made for nobody

  Scenario: Gary cannot roll for somebody who is not at the table
    When I say "she steps up [[roll Mortisha 1d6 falling damage]]"
    Then the roll should be refused
    And the refusal should name "Mortisha"

  # ------------------------------------------------------------ the modifier
  #
  # Separate, because this one is mechanical rather than cosmetic and is a
  # bigger change than the rest of this file.
  #
  # `check` is offered character, dc and reason — and no modifier. `_run`
  # reads one anyway and gets nothing, so every check ever graded has been a
  # flat d20. "avoid collapse against 12" ignored John's dexterity entirely,
  # and a fighter and a wizard fall off the same plank equally often.
  #
  # The fix is not to let gary name a number: a modifier is a fact about a
  # sheet gary does not own, and inventing one is the thing the engines exist
  # to prevent. Gary names the ability; the sheet says the score and the
  # ruleset says what that score is worth.

  Scenario: A check uses the character's own modifier
    When I say "we cross the planks [[check John dex 12 avoid collapse]]"
    Then the check should have used a modifier of 3
    And the roll should read "1d20+3"

  # The argument for one call covering several people, made concrete: the
  # difficulty is shared and the ability is shared, but what each of them
  # brings to it is their own. A single modifier applied to everybody would
  # be the sheet being ignored again, one level up.
  Scenario: Everybody in a check brings their own modifier
    When I say "the planks give [[check Bramble,John dex 12 avoid collapse]]"
    Then "John" should have rolled "1d20+3"
    And "Bramble" should have rolled "1d20-1"

  Scenario: A check against an ability the system does not have
    When I say "we cross the planks [[check John luck 12 avoid collapse]]"
    Then the roll should be refused
    And the refusal should name "luck"

  # A check with no ability named is still a check. Plenty of them are
  # against nothing in particular, and refusing those would push gary back
  # into narrating the outcome itself.
  Scenario: A check with no ability is rolled flat
    When I say "we cross the planks [[check John 12 avoid collapse]]"
    Then the check should have used a modifier of 0

  # The same argument as the four-degree systems, one level down. First
  # edition has no single ability modifier — it has a different table per
  # ability and no general ability check to spend one on — so a sixteen is
  # worth nothing here that a ten is not. Applying the modern formula would
  # be quietly running third edition in a first edition game, which is the
  # drift the engines exist to stop.
  Scenario: A system with no ability modifiers does not invent them
    Given I started "The heath" on "add-1e" running "the-moaning-barrow"
    And "Osric" the fighter has dex 16, and is mine
    When I say "I edge along the lintel [[check Osric dex 12 balance]]"
    Then the check should have used a modifier of 0

  # ------------------------------------------------------- the roll's own hole
  #
  # Everything above keeps gary from asserting a modifier on a check, and none
  # of it mattered while `roll` still took a free-text NdM+K. Gary ran a whole
  # encounter through that hole — "1d20+1", "1d20+2", "1d20+3", "1d20+4" for
  # four characters' initiative, every number invented, every sheet a straight
  # ten. A rule that only binds the tool gary can route around is not a rule.

  Scenario: A roll for somebody takes plain dice
    When I say "roll for it [[roll John 1d20+3 initiative]]"
    Then the roll should be refused
    And the refusal should say the sheet decides the modifier

  Scenario: A roll for somebody can still name an ability
    When I say "roll for it [[roll John dex 1d20 initiative]]"
    Then the check should have used a modifier of 3

  # A roll about the world has no sheet behind it, so there is nothing for a
  # modifier to contradict — how far a thrown rock carries, how deep the water
  # is. Those stay free-form.
  Scenario: A roll about the world can still be modified
    When I say "how far does it carry [[roll 2d6+2 the throw]]"
    Then the roll should read "2d6+2"

  Scenario: A roll against an ability the system does not have
    When I say "roll for it [[roll John luck 1d20 initiative]]"
    Then the roll should be refused
    And the refusal should name "luck"
