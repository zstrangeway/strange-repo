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

  Scenario: Adding a character to a campaign
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    When I open that campaign
    And I add "Bramble" the "rogue"
    Then the page shows "Bramble"
    And the page shows "8/8"

  Scenario: A campaign with nobody in it asks for somebody
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    When I open that campaign
    Then the page shows "Nobody at the table yet"
    And I should not be able to say anything

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
    When I open that campaign
    Then the page shows what the adventure is about
    When I add "Bramble" the "rogue"
    Then gary should open the scene without my asking
    And the composer should be waiting for me afterwards
