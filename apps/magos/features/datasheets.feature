Feature: Looking up a datasheet
  As someone who cannot remember every profile
  I want a unit's stats, weapons and abilities in one answer
  So that I do not have to open five pages to resolve one attack

  # A datasheet in the export is spread over eight tables: the sheet itself,
  # its models' stats, its wargear, its abilities, its keywords, its unit
  # composition, its points, and who it can lead. Every one of those is a
  # join away from the datasheet id. Handing back one of them is not an
  # answer to "what is a Custodian Guard" — putting them together is the
  # whole job.
  #
  # Numbers here are placeholders and will be pinned to the real export when
  # the steps are written; the shapes are what is being agreed.

  Background:
    Given magos has a complete sync

  # -------------------------------------------------------------- finding one

  Scenario: By its exact name
    When I look up "Custodian Guard"
    Then I should get one datasheet
    And it should be the Adeptus Custodes one

  # Nobody types "Venerable Contemptor Dreadnought" correctly the first time.
  Scenario: By part of its name
    When I search datasheets for "contemptor"
    Then the results should include "Venerable Contemptor Dreadnought"

  Scenario: Case and punctuation should not matter
    When I search datasheets for "custodian guard"
    Then the results should include "Custodian Guard"

  # The same name appears under more than one faction, and picking one
  # silently is how somebody ends up quoting the wrong statline.
  Scenario: A name that several factions have
    When I search datasheets for a name more than one faction uses
    Then the results should name each faction that has it
    And magos should not pick one on my behalf

  Scenario: Narrowing by faction
    When I search datasheets for "captain" in the Space Marines
    Then every result should be a Space Marines datasheet

  Scenario: Nothing matches
    When I search datasheets for "Emperor's Own Breakfast Cereal"
    Then magos should say nothing matched
    And magos should not invent a datasheet

  # ------------------------------------------------------- what comes back

  Scenario: A datasheet comes back whole
    When I look up "Custodian Guard"
    Then the answer should include its statline
    And the answer should include its weapon profiles
    And the answer should include its abilities
    And the answer should include its keywords
    And the answer should include its unit composition
    And the answer should include its points cost

  # Multi-model units have more than one statline and the export keeps them
  # as separate rows. A sergeant with different stats is exactly the sort of
  # thing that gets lost when only the first row is read.
  Scenario: A unit whose models differ
    When I look up a datasheet with more than one model profile
    Then the answer should give each model's statline separately
    And each statline should be named

  Scenario: Weapon profiles keep their abilities
    When I look up a datasheet with a weapon that has keywords
    Then each weapon should carry its range, attacks, skill, strength, AP and damage
    And each weapon should carry its own abilities

  # Points live in their own table and are keyed by model count, because a
  # ten-model squad is not twice a five-model one.
  Scenario: Points for each size the unit comes in
    When I look up a datasheet that comes in more than one size
    Then the answer should give a cost for each size
    And each cost should say how many models it buys

  # The export marks a datasheet as attachable and lists what it can join.
  Scenario: A character that attaches to other units
    When I look up a character that can lead
    Then the answer should say which units it can lead
    And the answer should include what it confers on the unit it leads

  # Damaged brackets change a profile mid-game and live in their own columns.
  Scenario: A unit with a damaged bracket
    When I look up a vehicle with a damaged profile
    Then the answer should say at what wounds it becomes damaged
    And the answer should say what changes

  # ---------------------------------------------------- rules text a model reads

  # Every description field in the export is HTML: <b>, <br>, and
  # <span class="kwb"> around keywords. Handing that to a model wastes tokens
  # and reads badly if it is ever shown to a person; stripping it naively
  # welds words together where a <br> was the only thing separating them.
  Scenario: Rules text comes back readable
    When I look up a datasheet whose ability text is marked up
    Then the ability text should have no HTML tags in it
    And the line breaks in the original should still be line breaks
    And the keywords the original emphasised should still be distinguishable

  # -------------------------------------------------------------- browsing

  Scenario: Listing the factions
    When I ask magos for the factions
    Then I should get every faction in the export
    And each should carry the id the other tools take

  Scenario: Listing a faction's datasheets
    When I ask for the Adeptus Custodes datasheets
    Then every result should be an Adeptus Custodes datasheet
    And each should carry enough to look it up in full
