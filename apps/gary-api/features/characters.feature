Feature: Characters
  As someone with a campaign
  I want to make a character, or a party of them
  So that there is somebody in the story to be

  # A character belongs to a campaign, not to an account: the campaign is what
  # an account owns, and reaching a character means reaching through it. So a
  # character in a stranger's campaign answers 404 for the same reason the
  # campaign itself does.
  #
  # A party is one or more. Solo play is the common case and the one the UI
  # leads with, but nothing here assumes it.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"
    And I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"

  Scenario: Making a character
    When I add "Bramble" the rogue
    Then the response status should be 201
    And the response field "name" should be "Bramble"
    And the response field "character_class" should be "rogue"
    And the character should be level 1

  Scenario: A party of several
    Given I add "Bramble" the rogue
    And I add "Maud" the cleric
    When I read the party
    Then the response status should be 200
    And the party should be "Bramble", "Maud"

  Scenario: The party starts empty
    When I read the party
    Then the response status should be 200
    And the party should be empty

  Scenario: A character needs a name
    When I add "   " the rogue
    Then the response status should be 422

  Scenario: A character needs a class
    When I add "Bramble" the ""
    Then the response status should be 422

  # The classes a system has are the system's business, and gary should refuse
  # a warlock in a game that has none rather than let the model discover it
  # mid-scene.
  Scenario: A class the system does not have
    When I add "Bramble" the artificer in "add-1e"
    Then the response status should be 422
    And the response code should be "no_such_class"

  Scenario: A character in someone else's campaign
    Given another account has a campaign
    When I add "Bramble" the rogue to their campaign
    Then the response status should be 404

  Scenario: Reading someone else's party
    Given another account has a campaign
    When I read their party
    Then the response status should be 404

  Scenario: Making a character needs a session
    Given I am signed out
    When I add "Bramble" the rogue
    Then the response status should be 401
