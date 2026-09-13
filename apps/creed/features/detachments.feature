Feature: Detachments
  As someone deciding how to build an army
  I want to see what a detachment gives me before I commit to it
  So that I pick one for what it does rather than for its name

  # A detachment is the hinge of an 11th edition army: it decides the army
  # rule, the stratagems, the enhancements, and — new in this edition — how
  # many Detachment Points the army gets and what its Force Disposition is.
  #
  # Detachments.csv and Detachments_chapter_dp.csv are the two tables missing
  # from creed's first pass at the export. The second exists because DP is
  # not a property of the detachment alone: a Test Guard detachment gives
  # a different number to Black Templars than to Blood Angels.

  Background:
    Given creed has a complete sync

  # --------------------------------------------------------------- browsing

  Scenario: The detachments a faction has
    When I ask for the Test Guard detachments
    Then every result should be a Test Guard detachment
    And each should carry its Detachment Points
    And each should carry its Force Disposition

  Scenario: What one detachment gives an army
    When I ask what the "Shield Doctrine" detachment does
    Then I should get its detachment ability
    And I should get the stratagems it brings
    And I should get the enhancements it brings
    And I should get its Detachment Points and Force Disposition

  # ------------------------------------------------------ points by chapter

  # Detachments_chapter_dp.csv overrides the detachment's own dp for named
  # keywords. Reading only Detachments.csv gives the wrong number for exactly
  # the armies most likely to be asked about.
  Scenario: A detachment whose points depend on the chapter
    When I ask about a detachment that lists per-chapter Detachment Points
    Then creed should give the number for each chapter it names
    And creed should say which number applies without a listed chapter

  Scenario: A detachment with no per-chapter entry
    When I ask about a detachment with no per-chapter Detachment Points
    Then creed should give the detachment's own number
    And creed should not imply the number varies

  # ------------------------------------------------------------- comparing

  # The question somebody actually has is not "what is in this detachment"
  # but "which of these two should I run", and that is answered by putting
  # them beside each other.
  Scenario: Two detachments side by side
    When I compare two detachments of the same faction
    Then I should get each one's ability, points and disposition together
    And I should get what each brings that the other does not

  Scenario: A detachment nobody has
    When I ask about a detachment that is not in the export
    Then creed should say it found nothing
    And creed should suggest the detachments that faction does have
