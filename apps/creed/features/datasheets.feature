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
    Given creed has a complete sync

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
    And creed should not pick one on my behalf

  Scenario: Narrowing by faction
    When I search datasheets for "captain" in the Space Marines
    Then every result should be a Space Marines datasheet

  Scenario: Nothing matches
    When I search datasheets for "Emperor's Own Breakfast Cereal"
    Then creed should say nothing matched
    And creed should not invent a datasheet

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

  # Points are not a number per datasheet, and in 11th edition they are not
  # even a number per unit size. Datasheets_models_cost.csv is a flattened
  # rendering of the printed table: rows with an empty cost are section
  # headers, and the value rows under one belong to it until the next.
  #
  # Of 1,658 datasheets, 669 price by how many of that unit the army already
  # has — "YOUR 1ST TO 2ND UNITS COST" then "YOUR 3RD + UNIT COSTS", with
  # 1st/2nd+ and 1st-to-3rd/4th+ shapes too. A third section, "WARGEAR
  # OPTIONS", prices wargear per item.
  #
  # So a datasheet on its own cannot be quoted one price, and anything that
  # returns a single number is lying about 40% of the roster.
  Scenario: Points for each size the unit comes in
    When I look up a datasheet that comes in more than one size
    Then the answer should give a cost for each size
    And each cost should say how many models it buys

  Scenario: A unit that gets dearer the more of it you take
    When I look up a datasheet priced by how many you have taken
    Then the answer should give each tier
    And each tier should say which of your units it applies to
    And creed should not quote one price as though it were the price

  Scenario: Wargear that costs points
    When I look up a datasheet with priced wargear options
    Then the answer should list each option with its cost
    And those costs should be kept apart from the unit's own cost

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

  # Every description field in the export is HTML, and it is not the small
  # set it looks like at a glance. Across the abilities table alone: 807
  # spans, 580 table tags, 209 list tags, 257 <br>, plus links, images, and a
  # nonstandard <ky>. So this goes through markdownify rather than anything
  # hand-rolled — real tables and nested lists are exactly what a regex
  # stripper turns into a run-on sentence.
  #
  # Wahapedia marks rules keywords with <span class="kwb">. Stock markdownify
  # flattens that, and the emphasis is load-bearing: the rules mean something
  # different by TYRANIDS than by the word "tyranids". A converter subclass
  # keeps it.
  Scenario: Rules text comes back readable
    When I look up a datasheet whose ability text is marked up
    Then the ability text should have no HTML tags in it
    And the line breaks in the original should still be line breaks

  Scenario: Rules keywords keep their emphasis
    When I look up an ability that emphasises a keyword
    Then that keyword should still be emphasised in the markdown

  Scenario: A rule written as a table stays a table
    When I look up an ability whose text contains a table
    Then the answer should render it as a markdown table
    And no cell's text should have run into the next

  Scenario: A rule written as a list stays a list
    When I look up an ability whose text contains a list
    Then each item should still be its own item

  # -------------------------------------------------------------- browsing

  Scenario: Listing the factions
    When I ask creed for the factions
    Then I should get every faction in the export
    And each should carry the id the other tools take

  Scenario: Listing a faction's datasheets
    When I ask for the Adeptus Custodes datasheets
    Then every result should be an Adeptus Custodes datasheet
    And each should carry enough to look it up in full
