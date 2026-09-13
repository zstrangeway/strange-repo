Feature: Checking a list
  As someone about to send a list to an opponent
  I want to be told what is wrong with it
  So that the problems come up now rather than in front of somebody

  # This is the feature with the most room to do harm, because the failure
  # mode is not an error — it is a green tick on a list that is illegal.
  # Somebody who trusts that finds out at a tournament.
  #
  # So the rule creed holds to: it checks what the export encodes, and it
  # says plainly what it did not check. The export is a data dump of
  # datasheets and detachments, not a rules engine. Some constraints are in
  # it as structure (who can lead whom, which detachment an enhancement
  # belongs to, whether a datasheet can be taken at all). Others are core
  # rules that appear nowhere in these tables (how many of one datasheet an
  # army may take, battleline minimums, what a Warlord must be). Others
  # again are in the export only as English prose — an enhancement whose
  # eligibility reads "ADEPTUS CUSTODES model only" is a sentence, not a
  # field.
  #
  # Checking the first kind and being quiet about the rest would be the
  # worst of the three options.

  Background:
    Given creed has a complete sync

  # -------------------------------------------------- what the data can check

  Scenario: A list within its points limit
    Given a list for the Test Guard at 2000 points holding 1980 points
    When I check it
    Then the points check should pass

  Scenario: A list over its points limit
    Given a list for the Test Guard at 2000 points holding 2100 points
    When I check it
    Then the points check should fail
    And it should say by how much

  Scenario: A unit from the wrong faction
    Given a list for the Test Guard
    When I add a datasheet belonging to the Test Xenos
    And I check it
    Then the check should fail
    And it should name the unit and its faction

  # The export marks these, and the mark exists precisely because they read
  # as ordinary datasheets otherwise.
  Scenario: A datasheet that cannot be taken in a list at all
    Given a list for a faction with a virtual datasheet
    When I add that virtual datasheet
    And I check it
    Then the check should fail
    And it should say that datasheet can only be summoned

  # Datasheets_leader.csv is a plain pairing table, so this one is exactly
  # checkable and worth checking: an illegal attachment is easy to make and
  # invisible on a list sheet.
  Scenario: A character attached to a unit it cannot lead
    Given a list holding a character and a unit it cannot lead
    When I attach the character to that unit
    And I check it
    Then the check should fail
    And it should say which units that character can lead

  Scenario: A character attached to a unit it can lead
    Given a list holding a character and a unit it can lead
    When I attach the character to that unit
    And I check it
    Then the attachment check should pass

  Scenario: An enhancement from another detachment
    Given a list whose detachment is "Shield Doctrine"
    When I give a character an enhancement from a different detachment
    And I check it
    Then the check should fail
    And it should name the detachment that enhancement belongs to

  Scenario: An enhancement on a unit that is not a character
    Given a list holding a unit that is not a character
    When I give that unit an enhancement
    And I check it
    Then the check should fail

  Scenario: A list with no detachment chosen
    Given a list with units but no detachment
    When I check it
    Then the check should fail
    And it should say a detachment is needed

  # ----------------------------------------------- saying what it did not check

  # The load-bearing scenario in this file.
  Scenario: A clean check does not claim the list is legal
    Given a list with nothing creed can fault
    When I check it
    Then creed should say which checks passed
    And creed should say which rules it does not check
    And creed should not say the list is legal

  Scenario: The unchecked rules are named, not gestured at
    Given any list
    When I check it
    Then creed should name the core-rules constraints it cannot see
    And it should say those are not in the export rather than that they pass

  # An enhancement's eligibility is prose in the description field. creed can
  # show it to a person who can read it; it cannot decide it.
  Scenario: A constraint the export states only in prose
    Given a list with a character carrying an enhancement
    When I check it
    Then creed should show the enhancement's own eligibility wording
    And creed should say it has not verified that wording itself

  # --------------------------------------------------------- how it reports

  Scenario: Several things wrong at once
    Given a list with three separate problems
    When I check it
    Then all three should be reported
    And creed should not stop at the first

  Scenario: Every problem says which unit it is about
    Given a list with a problem in one unit
    When I check it
    Then the report should name that unit
    And the report should say what would fix it

  Scenario: Checking an empty list
    Given a list with no units
    When I check it
    Then creed should say the list is empty
    And creed should not report it as passing
