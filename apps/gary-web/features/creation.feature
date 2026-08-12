Feature: Making a character, in a browser
  As someone building a character
  I want to pick how my scores are decided and place them myself
  So that the character is mine before the game starts

  # The party page asks for a name and a class and nothing else, so every
  # character gary has ever made has straight tens. What is missing is not a
  # field — it is the step where a character stops being a name.
  #
  # Which methods are offered comes from the system, never from this page. A
  # list here would be a second place for the rules to live, and the first one
  # to go stale.

  Background:
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"

  Scenario: The page offers what the system offers
    When I open that campaign's party
    Then I should be able to choose how scores are decided
    And the choices should be the system's own

  Scenario: Rolling a set and placing it
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    Then I should see 6 scores to place
    When I place them and add "Bramble" the "rogue" as mine
    Then the page shows "Bramble"
    And the party should show what Bramble is made of

  Scenario: Rolling again before placing
    # Nobody is stopped from re-rolling: gary-api rolls it, so a re-roll costs
    # nothing that matters and refusing would only make people delete the
    # character and start again.
    When I open that campaign's party
    And I choose "roll 4d6, drop the lowest"
    And I roll for scores
    And I roll for scores again
    Then the scores should have changed

  Scenario: Taking the standard array instead
    When I open that campaign's party
    And I choose "the standard array"
    Then I should see 6 scores to place
    And there should be nothing to roll

  # Hit points are the class's and the constitution's, so the page shows what
  # they came to rather than asking for them.
  Scenario: Hit points follow from what was placed
    When I open that campaign's party
    And I choose "the standard array"
    And I place them and add "Bruna" the "fighter" as mine
    Then the party should not show "8/8"

  # A system that generates nothing says so where the choice would have been,
  # rather than showing an empty control.
  Scenario: A system that does not generate scores says so
    Given I already have a campaign on "pathfinder-2e"
    When I open that campaign's party
    Then the page should say scores cannot be generated for this system
    And I should still be able to add "Ket" the "rogue" as mine
