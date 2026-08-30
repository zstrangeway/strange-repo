Feature: Campaigns
  As someone who wants to play
  I want to see my campaigns and start new ones
  So that signing in lands me somewhere I can do something

  # Signing in lands here rather than on a greeting. "Welcome Home, Ada" was
  # scaffolding proving the session worked; a list of your games proves the
  # same thing and is also the thing you came for.

  Scenario: Signing in lands on the campaigns
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the campaigns page
    Then the page shows "Your campaigns"

  Scenario: The campaigns survive a reload
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the campaigns page
    And I reload the page
    Then the page shows "Your campaigns"

  # A new account's first screen is the empty one, so it has to lead
  # somewhere rather than just report that there is nothing.
  Scenario: An empty list offers a way out of itself
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the campaigns page
    Then the page shows "No campaigns yet"
    And there should be a way to start one

  Scenario: A campaign I already have is listed
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    When I open the campaigns page
    Then the page shows "A Light in the Deep"
    And the page shows "The Drowned Belfry"

  # The module list is a consequence of the system, so they are steps rather
  # than two dropdowns that can disagree — the pairing gary-api refuses.
  Scenario: Starting a campaign, system then module then model
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the new campaign page
    And I choose the system "Dungeons & Dragons 5th Edition"
    Then the page shows "The Drowned Belfry"
    When I choose the module "The Drowned Belfry"
    Then the page shows "Which model should run it"
    When I choose the model "Claude Opus 5"
    And I name it "A Light in the Deep" and start
    Then I should be on a campaign page
    And the page shows "A Light in the Deep"

  # The whole point of exposing the choice is that the numbers differ
  # enormously, so the numbers have to be on screen next to the names.
  Scenario: The models show what they cost
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the new campaign page
    And I choose the system "Dungeons & Dragons 5th Edition"
    And I choose the module "The Drowned Belfry"
    Then each model should show its price

  Scenario: A campaign needs a name
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the new campaign page
    And I choose the system "Dungeons & Dragons 5th Edition"
    And I choose the module "The Drowned Belfry"
    And I choose the model "Claude Opus 5"
    And I name it "" and start
    Then the page shows an error about the name

  # Building the party is a step of its own, before the table. Starting a
  # campaign lands here rather than on a page that cannot do anything yet.
  Scenario: Starting a campaign lands on building the party
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the new campaign page
    And I choose the system "Dungeons & Dragons 5th Edition"
    And I choose the module "The Drowned Belfry"
    And I choose the model "Claude Opus 5"
    And I name it "A Light in the Deep" and start
    Then I should be building the party
    And the page shows what the adventure is about

  Scenario: Making the character I play
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    When I open that campaign's party
    And I add "Bramble" the "rogue" as mine
    Then the page shows "Bramble"
    # Their hit points, whatever they came to. It used to say 8/8 here, which
    # was the number a character with no scores got — and every character had
    # no scores, because the page generated six and then asked you to type
    # them in. They arrive placed now, so a rogue's constitution is worth
    # something and the flat eight has stopped being the answer. What the card
    # owes is the hit points; what they are is the system's, and creation.feature
    # is where that is settled.
    And the party should show what Bramble is made of
    And the page should say "Bramble" is mine

  Scenario: Adding a companion for gary to play
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    When I open that campaign's party
    And I add "Bramble" the "rogue" as mine
    And I add "Maud" the "cleric" as a companion
    Then the page should say "Maud" is gary's

  # Nothing to open a scene for until somebody is mine, so the way in stays
  # shut and says why.
  Scenario: The way in is shut until one of them is mine
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    When I open that campaign's party
    Then I should not be able to take them in
    When I add "Bramble" the "rogue" as mine
    Then I should be able to take them in

  Scenario: Taking them into the game
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    When I open that campaign's party
    And I add "Bramble" the "rogue" as mine
    And I take them in
    Then I should be on a campaign page
    And gary should open the scene without my asking

  # "gary is setting the scene" while gary is doing nothing of the sort is the
  # page describing work that is not happening. Nothing will happen until
  # somebody is at the table, and that is what it should say.
  # A campaign whose party was never built has nothing on the table to show,
  # so the table is not where it sends you.
  Scenario: A campaign with nobody in it sends me back to build one
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    When I open that campaign
    Then I should be building the party

  Scenario: Signing out from a campaign
    Given I have signed in at google as "ada@example.com" named "Ada"
    When I open the campaigns page
    And I sign out
    Then I should be on the sign in page

  # A table where everyone has sat down and nobody has spoken. The game should
  # start by happening to you, not by asking what you do before anything has.
  Scenario: A new campaign drops you into a situation
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    When I open that campaign's party
    Then the page shows what the adventure is about
    When I add "Bramble" the "rogue" as mine
    And I take them in
    Then gary should open the scene without my asking
    And the composer should be waiting for me afterwards
    # The premise was on screen to cover the wait. Once the opening has
    # arrived it says the same thing twice, in worse prose the second time.
    And the page should have stopped repeating the premise
