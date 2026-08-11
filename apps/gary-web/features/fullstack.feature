@fullstack
Feature: The whole thing, for real
  As someone about to deploy gary
  I want a few paths exercised against a real gary-api and a real database
  So that the stub agreeing with itself cannot be the reason the suite is green

  # Every other spec here drives an in-memory stub of gary-api, which was
  # written from the same understanding that produced gary-api and so cannot
  # notice the two drifting apart. These run a real gary-api on a throwaway
  # database, through the real migrations, and are deliberately few — they
  # cost a Postgres and a Python process to run.
  #
  # The providers are still stood in for, but by gary-api's own stand-in
  # rather than this suite's: a real page, at a real URL, that the browser
  # navigates to and back from exactly as it would with Google.

  Scenario: Signing in for the first time and being welcomed
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    Then I should be on the home page
    And I should be signed in as "Ada"

  Scenario: Signing in, out, and back to the same account
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I sign out
    Then I should be on the sign in page
    When I open the home page
    Then I should be on the sign in page
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    Then I should be signed in as "Ada"

  Scenario: Renaming myself
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the profile page
    And I change my display name to "Ada Lovelace"
    Then the page shows a confirmation
    When I open the home page
    Then I should be signed in as "Ada Lovelace"

  # The one that would catch gary-api and gary-web disagreeing about what an
  # identity is: the same address at a different provider must not find the
  # account the first one opened.
  Scenario: The same address at another provider is another account
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the profile page
    And I change my display name to "Ada Lovelace"
    And I sign out
    And I open the sign in page
    And I sign in with facebook, agreeing as "2|ada@example.com|Ada"
    Then I should be signed in as "Ada"

  Scenario: Connecting a second provider reaches the same account
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the profile page
    And I connect facebook, agreeing as "2|ada@example.com|Ada"
    Then facebook should be connected
    When I change my display name to "Ada Lovelace"
    And I sign out
    And I open the sign in page
    And I sign in with facebook, agreeing as "2|ada@example.com|Ada"
    Then I should be signed in as "Ada Lovelace"

  # The one that proves the stream is a stream. Everywhere else the frames
  # come from this suite's own stub, which was written to agree with what the
  # page expects; here they come from a real gary-api over a real SSE
  # connection, through the real dice and the real world engine.
  #
  # The model is still stood in for, on the same argument as the providers:
  # a real one costs money and answers differently every time. gary-api's
  # double reads directives out of the message, which is why the roll below
  # is asked for in the message itself.
  Scenario: Starting a campaign and playing a turn, for real
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the new campaign page
    And I choose the system "Dungeons & Dragons 5th Edition"
    And I choose the module "The Drowned Belfry"
    And I choose the model "Whatever gary is running"
    And I name it "A Light in the Deep" and start
    Then I should be building the party
    When I add "Bramble" the "rogue" as mine
    Then the page shows "8/8"
    When I take them in
    Then I should be on a campaign page
    When I say "I search the room [[roll 1d20+3 Perception]]"
    And gary finishes
    Then the transcript should show a roll of "1d20+3"
    And gary should answer
    And the transcript should show what I said

  # A reload has to get the table back: the stream only carries what happens
  # next, so everything before it comes from gary-api's transcript.
  Scenario: The table survives a reload, for real
    Given I am signed out
    When I open the sign in page
    And I sign in with google, agreeing as "1|ada@example.com|Ada"
    And I open the new campaign page
    And I choose the system "Dungeons & Dragons 5th Edition"
    And I choose the module "The Drowned Belfry"
    And I choose the model "Whatever gary is running"
    And I name it "A Light in the Deep" and start
    Then I should be building the party
    When I add "Bramble" the "rogue" as mine
    And I take them in
    And I say "I push open the door"
    And gary finishes
    And I reload the page
    Then the transcript should show what I said
    And the page shows "Bramble"
