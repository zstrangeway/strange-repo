Feature: Making a character, in a browser
  As someone building a character
  I want the score step to work the way the method I chose works
  So that I am arranging a character rather than transcribing one

  # Which methods are offered comes from the system, never from this page. A
  # list here would be a second place for the rules to live, and the first one
  # to go stale.
  #
  # What the page does with them is this page's, and it used to do one thing
  # for all of them: generate six numbers, print them, and then ask you to
  # type them into six boxes. The numbers were already on screen. Copying them
  # across is not a decision anybody came here to make, and getting one digit
  # wrong is a character you did not build.
  #
  # So the step reads the method rather than assuming one. Rolled and yours to
  # arrange means moving what you were given. Rolled in order means there is
  # nothing to decide. A point buy means spending. Only typing them in — which
  # is the method for scores worked out somewhere else — still has a box.

  Background:
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"

  Scenario: The page offers what the system offers
    When I open that campaign's party
    Then I should be able to choose how scores are decided
    And the choices should be the system's own

  # ------------------------------------------------- rolled, and yours to place

  Scenario: A rolled set arrives already placed
    # Nothing is asked of you before there is something to change. Every score
    # goes somewhere the moment it exists, in the order it came back, and the
    # step is arranging from there.
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    Then every ability should hold one of the rolled scores
    And there should be nothing to type

  Scenario: Swapping two scores with the arrows
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    And I move "dex" up
    Then "str" and "dex" should have swapped
    When I add "Bramble" the "rogue" as mine
    Then the party should show what Bramble is made of
    And Bramble should have the scores I arranged

  Scenario: The arrows stop at the ends
    # There is nothing above the first ability to swap with, and offering a
    # button that cannot do anything is worse than not offering one.
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    Then the first ability should not offer to move up
    And the last ability should not offer to move down

  Scenario: Dragging a score onto another ability swaps them
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    And I drag the score on "str" onto "con"
    Then "str" and "con" should have swapped

  Scenario: Taking a score the method had spare
    # The standard array is six numbers whatever a system's abilities are, so
    # a system with fewer leaves some over. They wait beside the sheet rather
    # than being dropped on the floor, and they can be brought in.
    When I open that campaign's party
    And I choose "the standard array"
    Then there should be scores waiting beside the sheet
    When I drag a waiting score onto "str"
    Then "str" should hold that score
    And the score it displaced should be waiting

  Scenario: Rolling again before placing
    # Nobody is stopped from re-rolling: gary-api rolls it, so a re-roll costs
    # nothing that matters and refusing would only make people delete the
    # character and start again.
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    And I roll for scores again
    Then the scores should have changed

  Scenario: Taking the standard array instead
    When I open that campaign's party
    And I choose "the standard array"
    Then every ability should hold one of the rolled scores
    And there should be nothing to roll

  # Hit points are the class's and the constitution's, so the page shows what
  # they came to rather than asking for them.
  Scenario: Hit points follow from what was placed
    When I open that campaign's party
    And I choose "the standard array"
    And I add "Bruna" the "fighter" as mine
    Then the party should not show "8/8"

  # -------------------------------------------------- rolled straight down the page

  Scenario: Rolled in order, with nothing to arrange
    # Three dice down the page is the whole of first edition's character
    # creation. There is nothing left to decide, so the page offers nothing to
    # decide it with — no arrows, no dragging and no boxes.
    Given I already have a campaign on "add-1e"
    When I open that campaign's party
    And I choose "roll 3d6 in order"
    And I roll for scores
    Then every ability should hold one of the rolled scores
    And there should be nothing to type
    And there should be nothing to move

  # ---------------------------------------------------------------- point buy

  Scenario: Spending a budget with the steppers
    When I open that campaign's party
    And I choose "point buy"
    Then every ability should start at the cheapest score the table prices
    And nothing should be spent yet
    When I raise "str" 3 times
    Then "str" should read 11
    And the spend should be 3 of 27

  Scenario: The budget stops the steppers
    # Raised as far as the page allows rather than to a number written here:
    # what the budget buys is the system's arithmetic, and a spec that did the
    # sum itself would be a second place for the table to live.
    When I open that campaign's party
    And I choose "point buy"
    And I raise every ability as far as the page will let me
    Then the spend should never have gone over 27
    And I should not be able to raise "con"

  Scenario: The table's ends stop the steppers
    When I open that campaign's party
    And I choose "point buy"
    Then I should not be able to lower "str"
    When I raise "str" to the top of the table
    Then I should not be able to raise "str"

  # ------------------------------------------------------------------ typing

  # Not a method so much as the absence of one: somebody who rolled at a real
  # table, or built a character by a rule gary does not implement, already has
  # an answer and needs somewhere to put it. This is the one method where a
  # box is the point, so it keeps one.
  Scenario: Typing them in myself
    When I open that campaign's party
    And I choose "type them in"
    Then I should be able to type each score
    And there should be nothing to roll
    When I type 16 for "dex" and add "Bramble" the "rogue" as mine
    Then the party should show what Bramble is made of

  Scenario: Nudging a typed score rather than retyping it
    When I open that campaign's party
    And I choose "type them in"
    And I type 16 for "dex"
    And I raise "dex" 1 times
    Then "dex" should read 17

  Scenario: Typing in a score the system will not have
    When I open that campaign's party
    And I choose "type them in"
    And I type 30 for "dex" and add "Bramble" the "rogue" as mine
    Then the page shows an error about the score

  # ----------------------------------------------------------- generating nothing

  # A system that generates nothing says so where the choice would have been,
  # rather than showing an empty control — and still lets you type, which is
  # the only way to make a Pathfinder character with scores at all.
  Scenario: A system that does not generate scores still lets me type
    Given I already have a campaign on "pathfinder-2e"
    When I open that campaign's party
    Then the page should say scores cannot be generated for this system
    And I should be able to choose "type them in"
    And I should still be able to add "Ket" the "rogue" as mine

  # ------------------------------------------------------------- switching away

  Scenario: Changing my mind about the method
    # What the last method produced is not what this one would, so nothing
    # carries over — a spread half-arranged under one method and half spent
    # under another is nobody's character.
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    And I choose "point buy"
    Then every ability should start at the cheapest score the table prices
    And there should be nothing waiting beside the sheet
