Feature: Choosing a model
  As someone starting a campaign
  I want to choose which model runs it
  So that I can spend what the game is worth to me

  # OpenRouter serves hundreds of models at prices two orders of magnitude
  # apart — the cheapest capable ones are around a sixtieth of the dearest on
  # output — so which one runs a campaign is worth exposing rather than baking
  # into a constant.
  #
  # Only models that can call tools are offered, and that is the one rule the
  # API enforces rather than leaves to the person choosing. gary's whole design
  # is the model going through the engines: it asks for a check, the rules
  # grade it, the world records it. A model that cannot call a tool cannot do
  # any of that, and it would not fail loudly — it would narrate a perfectly
  # plausible game that nothing was adjudicating, which is the worst failure
  # available here.
  #
  # Without a key gary offers a built-in list rather than nothing, so the app
  # still starts and still plays. That list is what these specs see.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"

  Scenario: The models gary can run
    When I GET "/models"
    Then the response status should be 200
    And every model should carry a name and a price
    And every model offered should be able to call tools
    And some models should be suggested

  # A menu, like the catalogue. What gary can be run on is part of deciding
  # whether to make an account.
  Scenario: The menu needs no session
    Given I am signed out
    When I GET "/models"
    Then the response status should be 200

  Scenario: Starting a campaign on a chosen model
    When I start "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry" with "deepseek/deepseek-v3.2"
    Then the response status should be 201
    And the campaign should run on "deepseek/deepseek-v3.2"

  # Naming no model is the common case and has to keep working, so the column
  # is nullable and the deployment's default fills in. A campaign started
  # before models were selectable reads exactly the same way.
  Scenario: A campaign that names no model runs on the default
    When I start "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    Then the response status should be 201
    And the campaign should run on the default model

  Scenario: A model that cannot call tools is refused
    When I start "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry" with "nobody/cannot-call-tools"
    Then the response status should be 422
    And the response code should be "unsupported_model"

  Scenario: Changing the model mid-campaign
    Given I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    When I move that campaign to "anthropic/claude-haiku-4.5"
    Then the response status should be 200
    And the campaign should run on "anthropic/claude-haiku-4.5"

  Scenario: Changing back to the default
    Given I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry" with "deepseek/deepseek-v3.2"
    When I move that campaign to the default model
    Then the response status should be 200
    And the campaign should run on the default model

  Scenario: Changing to a model that cannot call tools
    Given I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    When I move that campaign to "nobody/cannot-call-tools"
    Then the response status should be 422
    And the response code should be "unsupported_model"

  Scenario: Changing someone else's campaign
    Given another account has a campaign
    When I move their campaign to "anthropic/claude-haiku-4.5"
    Then the response status should be 404

  Scenario: Changing a model needs a session
    Given I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    And I am signed out
    When I move that campaign to "anthropic/claude-haiku-4.5"
    Then the response status should be 401

  # The model a campaign runs on is what gary is actually asked, so it travels
  # with the turn rather than being read from the environment at the last
  # moment. Two campaigns on one deployment can be on different models.
  Scenario: The campaign's model is the one gary is asked for
    Given I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry" with "deepseek/deepseek-v3.2"
    And I add "Bramble" the rogue
    When I say "I push open the door"
    Then the turn should stream to completion
    And gary should have been asked for "deepseek/deepseek-v3.2"
