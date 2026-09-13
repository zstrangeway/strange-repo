Feature: Working out an attack
  As someone deciding where to point a unit
  I want the arithmetic done from the real profiles
  So that the answer comes from the datasheet rather than from a guess

  # This is the half of "rules and stats" that a language model is worst at
  # unaided: it will confidently produce a wound roll that is one pip off,
  # and the answer looks exactly as plausible as the right one. Doing it in
  # code and handing back the number is the entire point.
  #
  # Every input comes from the synced tables — the attacker's weapon row out
  # of Datasheets_wargear.csv, the target's T, Sv, invulnerable save and W
  # out of Datasheets_models.csv. Nothing here takes a statline typed by
  # hand when a datasheet name would do, because a typed statline is a
  # second place for the numbers to be wrong.

  Background:
    Given creed has a complete sync

  # ------------------------------------------------------------- the basics

  Scenario: One unit shooting another
    When I work out "Testudo Guard" shooting at a target datasheet
    Then I should get the chance to hit
    And I should get the chance to wound
    And I should get the chance the save fails
    And I should get the damage I should expect

  Scenario: The wound roll comes off the strength and toughness table
    When I work out an attack of strength 4 against toughness 4
    Then the wound roll needed should be 4+

  Scenario: Strength double the toughness
    When I work out an attack of strength 8 against toughness 4
    Then the wound roll needed should be 2+

  Scenario: Strength greater but not double
    When I work out an attack of strength 5 against toughness 4
    Then the wound roll needed should be 3+

  Scenario: Strength less than toughness
    When I work out an attack of strength 3 against toughness 4
    Then the wound roll needed should be 5+

  Scenario: Strength half the toughness or less
    When I work out an attack of strength 2 against toughness 4
    Then the wound roll needed should be 6+

  # --------------------------------------------------------------- saving

  Scenario: Armour worsened by AP
    When I work out an attack with AP -1 against a 3+ save
    Then the save needed should be 4+

  # Taking the better of the two is the step most often got wrong by hand,
  # because the invulnerable save is on a different part of the datasheet.
  Scenario: An invulnerable save that beats the armour
    When I work out an attack with AP -3 against a 3+ save and a 4+ invulnerable
    Then the save used should be the invulnerable one

  Scenario: An invulnerable save the armour still beats
    When I work out an attack with AP -1 against a 2+ save and a 4+ invulnerable
    Then the save used should be the armour one

  Scenario: A save that AP has pushed off the table
    When I work out an attack with AP -4 against a 5+ save and no invulnerable
    Then there should be no save

  # -------------------------------------------------------------- damage

  Scenario: Damage that overkills
    When I work out a damage 3 weapon against a 1-wound model
    Then the spilled damage should not carry to the next model
    And the expected kills should reflect that

  Scenario: Damage that takes more than one hit to kill
    When I work out a damage 1 weapon against a 3-wound model
    Then the expected kills should account for the wounds needed

  Scenario: A weapon with a variable number of attacks
    When I work out a weapon whose attacks are a dice roll
    Then the expected attacks should use the average of that dice

  # ------------------------------------------------- the abilities on the weapon

  # These come off the weapon's own row, so creed applies the ones it can
  # read and says so — an answer that silently ignores Sustained Hits is
  # wrong in the direction that loses games.
  Scenario: A weapon that hits automatically
    When I work out a weapon with Torrent
    Then the hit step should be skipped
    And the answer should say why

  Scenario: A weapon that re-rolls its wound roll
    When I work out a weapon with Twin-linked
    Then the wound chance should account for the re-roll

  Scenario: A weapon with Sustained Hits
    When I work out a weapon with Sustained Hits
    Then the extra hits should be in the expected damage

  Scenario: A weapon with Lethal Hits
    When I work out a weapon with Lethal Hits
    Then the hits that wound automatically should skip the wound roll

  Scenario: A weapon with Devastating Wounds
    When I work out a weapon with Devastating Wounds
    Then the critical wounds should bypass the save

  # The honesty scenario. A weapon ability creed does not model must be
  # visible, not quietly dropped — the number is wrong either way, but only
  # one of those lets somebody notice.
  Scenario: An ability creed does not model
    When I work out a weapon carrying an ability creed cannot apply
    Then the answer should name that ability
    And the answer should say it was not applied
    And the answer should still give the arithmetic it did do

  Scenario: Saying what it assumed
    When I work out any attack
    Then the answer should state the modifiers it applied
    And the answer should be reproducible from what it states

  # ------------------------------------------------------------- comparing

  # The real question is usually "which of these two should shoot it".
  Scenario: Which of my units is better into a target
    When I compare two of my units shooting the same target
    Then I should get the expected damage of each
    And I should get which is better and by how much

  Scenario: What a unit is best used against
    When I ask what a unit's weapons are best into
    Then I should get its expected damage against a spread of toughness and saves

  # ------------------------------------------------------------ when it can't

  Scenario: A profile with something creed cannot read
    When I work out an attack whose profile has a value creed cannot parse
    Then creed should say which value it could not read
    And creed should not substitute a number of its own
