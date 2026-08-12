Feature: Making a character
  As someone building a character
  I want scores generated the way my edition generates them
  So that a fighter and a wizard are different people before anybody rolls

  # Every character gary has ever made has straight tens and eight hit points.
  # Everything downstream of a sheet is built and correct — a check names an
  # ability, the sheet answers, the ruleset converts — and none of it shows,
  # because ten is worth nothing in every system gary runs. A fighter and a
  # wizard climb the same rope equally well and take the same beating.
  #
  # WHICH METHODS EXIST IS THE SYSTEM'S TO SAY. Not a global list with
  # exceptions: an edition permits what it permits, the player picks from what
  # their edition permits, and asking for one it does not offer is refused the
  # same way an unknown class is. This is the same argument as four degrees of
  # success and per-system ability modifiers, one step earlier in the game.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"

  # --------------------------------------------------------- what is offered

  Scenario: A system says how its characters are made
    When I read the system "dnd-5e"
    Then it should offer the standard array
    And it should offer point buy
    And it should offer rolling 4d6 and dropping the lowest
    And it should offer typing them in

  # First edition rolls three dice straight down the page and you play what
  # you got, which is a different thing from arranging six numbers — the DMG's
  # own Method I offers the arranging kind too, so it offers both.
  Scenario: First edition offers its own two
    When I read the system "add-1e"
    Then it should offer rolling 3d6 in order
    And it should offer rolling 4d6 and dropping the lowest
    And it should not offer point buy

  # Typing them in is offered by everything, because it is not a method so
  # much as the absence of one: somebody who rolled at a real table, or built
  # a character by a rule gary does not implement, has an answer already and
  # needs somewhere to put it.
  Scenario: Every system lets you type them in
    Then every system should offer typing them in

  # Which is what gives Pathfinder a way in. It generates nothing — everyone
  # starts at ten and takes boosts from ancestry, background and class, none
  # of which gary has, and inventing a method would be quietly running 5e's
  # rule in a Pathfinder game. But somebody who worked their scores out
  # properly can type the result, and that is a better answer than refusing
  # to make the character at all.
  Scenario: Pathfinder generates nothing, and says so
    When I read the system "pathfinder-2e"
    Then it should offer no way of generating scores
    And it should say why
    But it should offer typing them in

  # ------------------------------------------------------------- rolling one

  Scenario: Rolling a set of scores
    Given I have a campaign on "dnd-5e"
    When I roll scores with "roll-4d6-drop-lowest"
    Then I should get 6 scores
    And each should be between 3 and 18
    And the roll should be recorded as dice, not as a number

  Scenario: Rolling in order gives them already placed
    Given I have a campaign on "add-1e"
    When I roll scores with "roll-3d6-in-order"
    Then the scores should already be assigned to abilities
    And each should be between 3 and 18

  Scenario: Rolling a way this system does not offer
    Given I have a campaign on "dnd-5e"
    When I roll scores with "roll-3d6-in-order"
    Then the response status should be 422
    And the refusal should name the method

  Scenario: Rolling for a system that generates nothing
    Given I have a campaign on "pathfinder-2e"
    When I roll scores with "roll-4d6-drop-lowest"
    Then the response status should be 422

  Scenario: There is nothing to roll for typing them in
    Given I have a campaign on "dnd-5e"
    When I roll scores with "manual"
    Then the response status should be 422

  # The dice are gary-api's and not the client's, for exactly the reason they
  # are not the model's: a number a browser sent is a number somebody typed.
  Scenario: The dice belong to the API
    Given I have a campaign on "dnd-5e"
    And the dice are seeded
    When I roll scores with "roll-4d6-drop-lowest"
    And I roll scores with "roll-4d6-drop-lowest" again
    Then the two sets should differ

  # ---------------------------------------------------------- making one

  # However the numbers were arrived at, they arrive here the same way: the
  # endpoint takes scores and does not care whether dice, a table or a person
  # produced them. Which is what makes typing them in free.
  Scenario: A character made with scores keeps them
    Given I have a campaign on "dnd-5e"
    When I add "Bramble" the rogue with dex 16 and con 14
    Then "Bramble" should have dex 16
    And a check on their dexterity should use a modifier of 3

  Scenario: Scores typed in for a system that generates none
    Given I have a campaign on "pathfinder-2e"
    When I add "Ket" the rogue with dex 18 and con 14
    Then "Ket" should have dex 18

  Scenario: A character made with nothing still works
    # Not everybody wants to arrange six numbers, and a campaign started
    # before this existed has characters who never did.
    Given I have a campaign on "dnd-5e"
    When I add "Bramble" the rogue
    Then "Bramble" should have dex 10

  Scenario: A score outside what the system allows
    Given I have a campaign on "dnd-5e"
    When I add "Bramble" the rogue with dex 30
    Then the response status should be 422

  Scenario: An ability the system does not have
    Given I have a campaign on "dnd-5e"
    When I add "Bramble" the rogue with luck 16
    Then the response status should be 422
    And the refusal should name "luck"

  # ---------------------------------------------------------- hit points

  # The other half of the same problem: every character has eight hit points
  # whatever they are, which stopped being cosmetic the moment fights existed.
  # A hit die is the class's and the constitution modifier is the sheet's, so
  # neither is anybody's to type in.
  Scenario: Hit points come from the class and the constitution
    Given I have a campaign on "dnd-5e"
    When I add "Bruna" the barbarian with con 16
    Then "Bruna" should have 15 hit points

  Scenario: A wizard is not a barbarian
    Given I have a campaign on "dnd-5e"
    When I add "Bruna" the barbarian with con 10
    And I add "Wren" the wizard with con 10
    Then "Bruna" should have more hit points than "Wren"

  Scenario: A frail character still has one hit point
    # A constitution modifier can be worse than the hit die is big, and a
    # character created already dead is nobody's idea of a rule.
    Given I have a campaign on "dnd-5e"
    When I add "Wren" the wizard with con 3
    Then "Wren" should have 1 hit point

  Scenario: A system with no hit dice yet keeps the default
    # Pathfinder's hit points are ancestry plus class plus constitution, and
    # there are no ancestries. Refusing to make characters at all would be
    # worse than a stated default, so the default stays and says so.
    Given I have a campaign on "pathfinder-2e"
    When I add "Ket" the rogue
    Then "Ket" should have 8 hit points
