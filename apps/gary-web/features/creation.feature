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
  # arrange means choosing which ability takes which number. Rolled in order
  # means there is nothing to decide. A point buy means spending. Only typing
  # them in — which is the method for scores worked out somewhere else — still
  # has a box.
  #
  # Arranging is a choice per ability, not a gesture. It was dragging first,
  # and dragging is the fussiest way anybody has found to say "that number goes
  # there": it wants aim, it wants a mouse, and it asks a question of your hands
  # rather than of your character. Every tool that has solved this — Roll20's
  # charactermancer, the array assigners, the builders — puts a chooser on each
  # ability and lists what is going spare in it. The one bug those tools are
  # reported for is letting the same number be taken twice, so taking one that
  # is already somewhere trades places with it here.
  #
  # And each one says what it is worth, because +2 is the thing being placed
  # and 15 is only how the system writes it down.

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
    # step is rearranging from there.
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    Then every ability should hold one of the rolled scores
    And there should be nothing to type

  Scenario: Each score says what it is worth
    # A 15 is not what anybody is choosing between; a +2 is. What it is worth
    # is the system's to say, and the page shows what it said.
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    Then every ability should say what its score is worth

  Scenario: Giving an ability a different score
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    And I give "dex" the score that was on "str"
    Then "str" and "dex" should have swapped
    When I add "Bramble" the "rogue" as mine
    Then the party should show what Bramble is made of

  Scenario: Every ability offers the whole set
    # Including the ones already somewhere, because taking one of those is how
    # you swap two scores, and hiding them would leave no way to.
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    Then each ability should offer every rolled score

  Scenario: The set survives being rearranged
    # The scores are the method's and arranging them is only arranging: one
    # cannot be taken twice, and none can go missing. That is the bug these
    # choosers are reported for everywhere else.
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    And I give "dex" the score that was on "str"
    And I give "con" the score that was on "dex"
    Then the sheet should still hold the whole rolled set

  Scenario: Taking a score the method had spare
    # The standard array is six numbers whatever a system's abilities are, so a
    # system with fewer leaves some over. They are listed as going spare, and
    # taking one puts what it displaced back among them.
    When I open that campaign's party
    And I choose "the standard array"
    Then there should be scores going spare
    When I give "str" a score that was going spare
    Then "str" should hold that score
    And the score it displaced should be going spare

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
    # decide it with — nothing to choose from and no boxes.
    Given I already have a campaign on "add-1e"
    When I open that campaign's party
    And I choose "roll 3d6 in order"
    And I roll for scores
    Then every ability should hold one of the rolled scores
    And there should be nothing to type
    And there should be nothing to choose
    # And no modifiers, because first edition has none to show: it has a table
    # per ability and no general one, which gary-api says by answering nothing
    # rather than by quietly halving the distance from ten.
    And no score should say it is worth anything

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
    And there should be nothing going spare
