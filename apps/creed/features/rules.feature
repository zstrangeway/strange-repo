Feature: Looking up stratagems, abilities and enhancements
  As someone mid-turn with a decision to make
  I want to find the stratagem that applies right now
  So that I am not scrolling a detachment page while the clock runs

  # Stratagems are the largest table in the export and the one most often
  # wanted under time pressure. They are filtered in play by three things at
  # once: whose turn it is, which phase, and which detachment — so those are
  # the filters, rather than a name search somebody has to already know the
  # answer to.

  Background:
    Given creed has a complete sync

  # ------------------------------------------------------------ stratagems

  Scenario: By name
    When I look up the stratagem "BRACE"
    Then I should get that stratagem
    And it should carry its CP cost
    And it should carry when it can be used and what it does

  Scenario: What I can do in a phase
    When I ask for stratagems in the Shooting phase
    Then every result should be usable in the Shooting phase

  Scenario: Only the ones for my turn
    When I ask for stratagems in my own turn
    Then no result should be an opponent's-turn-only stratagem

  # A stratagem from a detachment you are not running is noise at best and a
  # rules mistake at worst.
  Scenario: Only the ones my detachment has
    When I ask for stratagems in a named detachment
    Then every result should belong to that detachment or to the core rules

  Scenario: Only the ones I can afford
    When I ask for stratagems costing at most 1 CP
    Then no result should cost more than 1 CP

  Scenario: Filters combine
    When I ask for my own turn, Shooting phase, at most 1 CP
    Then every result should satisfy all three

  Scenario: A unit's own stratagems
    When I ask which stratagems apply to "Testudo Guard"
    Then the results should be the ones the export ties to that datasheet

  # ------------------------------------------------------------- abilities

  Scenario: Looking up a named ability
    When I look up the ability "Testudo Resolve"
    Then I should get its rules text
    And it should say which faction it belongs to

  # ---------------------------------------------------------- enhancements

  Scenario: Enhancements in a detachment
    When I ask for the enhancements in a named detachment
    Then every result should belong to that detachment
    And each should carry its points cost
    And each should say which models can take it

  # ------------------------------------------------- detachment abilities

  Scenario: What a detachment gives an army
    When I ask what a named detachment does
    Then I should get its detachment ability
    And I should get the stratagems it brings
    And I should get the enhancements it brings

  # -------------------------------------------------------------- honesty

  # The failure that matters most here is a confident wrong answer. A
  # stratagem that does not exist, invented from the shape of the question,
  # is worse than no answer at all — somebody will spend a CP on it.
  Scenario: A stratagem nobody has
    When I look up a stratagem that is not in the export
    Then creed should say it found nothing
    And creed should not describe a stratagem it does not have

  Scenario: A phase that is not a phase
    When I ask for stratagems in the "Breakfast phase"
    Then creed should say which phases there are
    And creed should not return an empty list as though it were an answer
