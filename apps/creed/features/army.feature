Feature: Building an army list
  As someone putting a list together before a game
  I want units added up as I go, priced the way the book prices them
  So that I find out I am 30 points over now rather than at the table

  # A list is the one thing in creed that belongs to the person rather than
  # to the export, so it is the one thing that is written down. It lives in
  # the same SQLite file, alongside the synced tables rather than inside
  # them: a sync replaces every export table wholesale, and it must never
  # take somebody's list with it.
  #
  # Pricing is the hard part, and it is hard for a reason specific to this
  # edition — see the points comments in datasheets.feature. A unit's cost
  # depends on how many of that datasheet the list already has, so a list is
  # not the sum of its units priced independently. Adding a third unit can
  # change nothing about the first two, or can cost more than the first one
  # did, and the difference is not visible from the datasheet alone.

  Background:
    Given creed has a complete sync

  # ----------------------------------------------------------- starting one

  Scenario: Starting a list
    When I start a list for the Adeptus Custodes at 2000 points
    Then the list should be empty
    And the list should know its faction and its points limit

  Scenario: Choosing a detachment
    Given a list for the Adeptus Custodes at 2000 points
    When I set its detachment to "Talons Of The Emperor"
    Then the list should carry that detachment
    And the list should carry that detachment's Detachment Points

  Scenario: A detachment the faction does not have
    Given a list for the Adeptus Custodes at 2000 points
    When I set its detachment to one belonging to another faction
    Then creed should refuse
    And creed should say which detachments that faction has

  # ------------------------------------------------------------ adding units

  Scenario: Adding a unit
    Given a list for the Adeptus Custodes at 2000 points
    When I add a "Custodian Guard" at its smallest size
    Then the list should hold one unit
    And the list's total should be that unit's cost

  Scenario: Adding a unit at a size it comes in
    Given a list for the Adeptus Custodes at 2000 points
    When I add a "Custodian Guard" of 10 models
    Then that unit should be priced at the 10-model cost

  Scenario: A size the unit does not come in
    Given a list for the Adeptus Custodes at 2000 points
    When I add a "Custodian Guard" of 7 models
    Then creed should refuse
    And creed should say which sizes it comes in

  Scenario: Removing a unit
    Given a list holding three units
    When I remove the second
    Then the list should hold the other two
    And the total should have come down by what it cost

  # --------------------------------------------------- pricing that escalates

  # The scenario the flat-price assumption gets wrong. 669 of 1,658
  # datasheets price this way, so this is not an edge case.
  Scenario: The third one costs more than the first
    Given a list whose faction has a unit priced by how many you take
    When I add a third of that unit
    Then that third unit should be priced at the higher tier
    And the first two should still be priced at the lower one

  Scenario: Removing one re-prices the rest
    Given a list holding three of a unit priced by how many you take
    When I remove one of them
    Then the remaining two should be priced at the lower tier
    And the total should reflect that, not just the removed unit's cost

  Scenario: Priced wargear adds to the unit
    Given a list holding a unit with priced wargear options
    When I add two of a priced option to it
    Then that unit's cost should include both
    And the list should show the wargear cost apart from the unit's own

  Scenario: An enhancement costs points
    Given a list with a detachment and a character who can take one
    When I give that character an enhancement
    Then the enhancement's cost should be in the list's total

  # --------------------------------------------------------------- reading it

  Scenario: Seeing the list
    Given a list holding several units
    When I ask to see it
    Then I should get each unit, its size and its cost
    And I should get the total and what remains of the limit

  Scenario: Knowing how much room is left
    Given a list for the Adeptus Custodes at 2000 points holding 1750 points
    When I ask to see it
    Then creed should say 250 points remain

  Scenario: A list over its limit
    Given a list for the Adeptus Custodes at 2000 points
    When I add units coming to 2100 points
    Then creed should say it is 100 points over
    And creed should still let me see the list

  # A list somebody is mid-way through is not a broken list, and creed
  # refusing to add the fourth unit because the third made it illegal is how
  # a tool becomes something people work around.
  Scenario: Going over is a warning, not a refusal
    Given a list for the Adeptus Custodes at 2000 points holding 1990 points
    When I add a unit costing 200 points
    Then the unit should be added
    And creed should warn that the list is over

  # ------------------------------------------------------------- keeping it

  Scenario: A list survives a sync
    Given a list holding several units
    When the export updates and creed re-syncs
    Then the list should still be there
    And it should still hold the same units

  # Prices move with a dataslate — that is the reason the app checks for
  # updates at all. A list silently re-totalling overnight is the version of
  # that which loses somebody a game.
  Scenario: A sync that changes a price says so
    Given a list holding a unit whose cost changes in the next sync
    When the export updates and creed re-syncs
    Then the list's total should use the new cost
    And creed should say which units changed price and by how much

  Scenario: A sync that removes a datasheet the list uses
    Given a list holding a unit that the next sync no longer has
    When the export updates and creed re-syncs
    Then creed should keep the unit in the list
    And creed should say that datasheet is no longer in the export

  Scenario: More than one list
    Given a list for the Adeptus Custodes
    And a list for the Astra Militarum
    When I ask for my lists
    Then I should get both
    And working on one should not touch the other
