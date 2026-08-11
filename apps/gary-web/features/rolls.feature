Feature: Rolls on the table
  As someone watching a turn arrive
  I want each roll to say whose it was
  So that a column of numbers reads as things happening to people

  # What is on screen today, for a turn where the causeway gave way under a
  # party of four:
  #
  #   1d20   →  9   avoid collapse against 12 · rolled 9      failure
  #   1d20+2 →  4   strength of timbers · rolled 2
  #   1d6    →  5   falling damage · rolled 5
  #   1d20   →  6   avoid collapse against 12 · rolled 6      failure
  #
  # Two identical-looking saves, two people, and no way to tell which is
  # which. The name is the one piece of context that makes the rest legible.

  Background:
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"

  Scenario: A roll says whose it is
    When I open that campaign's party
    And I add "Bramble" the "rogue" as mine
    And I add "John" the "fighter" as a companion
    And I take them in
    And I say "we cross the planks" and gary checks "John"
    And gary finishes
    Then the roll should be labelled "John"
    And the roll should say what it was against
    And the roll should show how the total was reached

  # A roll about the world rather than about a person — how sound the timbers
  # are, what the weather does — has nobody to name, and inventing one would
  # be worse than leaving it off.
  Scenario: A roll about the world names nobody
    When I open that campaign's party
    And I add "Bramble" the "rogue" as mine
    And I take them in
    And I say "how sound are these planks" and gary rolls
    And gary finishes
    Then the roll should be labelled with nobody
