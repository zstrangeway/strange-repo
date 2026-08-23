Feature: Advancement on the table
  As someone whose character just got better at surviving
  I want to see it happen and see how far the next one is
  So that a long campaign has something on screen that moves

  # The party card has said "level 1 rogue" for every character in every
  # campaign ever made here, because nothing could write that number. Once
  # something can, the card is where it shows — and a level is a mechanical
  # fact, so it renders as its own element rather than as prose.
  #
  # That distinction is the same one rolls are drawn on. Gary saying "you feel
  # stronger, Bramble" in a paragraph is indistinguishable from gary deciding
  # you levelled, which is precisely what the engine exists to take out of its
  # hands. A frame the page renders as a frame cannot be faked in a sentence.

  Background:
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    And I open that campaign's party
    And I add "Bramble" the "rogue" as mine
    And I take them in

  # ------------------------------------------------------------- on the card

  # The numbers are a fold over the log rather than something this page keeps,
  # for the fight order's reason: it renders a fact rather than tracking one.
  Scenario: The party card says how far along somebody is
    Then "Bramble" should show as level 1
    And "Bramble" should show 0 of the 300 they need

  # ------------------------------------------------------- as a turn arrives

  Scenario: An award arrives as its own element
    When I say "it stops moving" and gary awards "Bramble" 300
    And gary finishes
    Then the transcript should show an award to "Bramble"
    And the award should say what it was for

  Scenario: A level says what it brought
    When I say "it stops moving" and gary awards "Bramble" 300
    And gary finishes
    Then the transcript should show "Bramble" reaching level 2
    And it should say what hit points that brought

  Scenario: The card moves when the turn does
    When I say "it stops moving" and gary awards "Bramble" 300
    And gary finishes
    Then "Bramble" should show as level 2

  # An award that crossed nothing is still worth showing — "300 of the 900 you
  # need" is the thing that makes a long campaign feel like it is going
  # somewhere, and it is the whole reason the next level's cost is on the card.
  Scenario: An award that levels nobody still shows
    When I say "you scrape through" and gary awards "Bramble" 100
    And gary finishes
    Then the transcript should show an award to "Bramble"
    And "Bramble" should show as level 1

  # ------------------------------------------------------------- and after

  # The stream only carries what happens next. Everything before it comes back
  # from gary-api's transcript, and a level that vanished on reload would be
  # the page having tracked it rather than read it.
  Scenario: A level survives a reload
    When I say "it stops moving" and gary awards "Bramble" 300
    And gary finishes
    And I reload the page
    Then "Bramble" should show as level 2
    And the transcript should show "Bramble" reaching level 2
