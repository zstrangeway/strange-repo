Feature: The opening
  As someone who has just made a character
  I want to be dropped into a situation
  So that the game starts by happening to me rather than by asking me a question

  # A campaign with a party and nothing said is a table where everyone has sat
  # down and nobody has spoken. What was on screen was an empty box captioned
  # "what do you do?" — which is the one question a game master is supposed to
  # have earned before asking.
  #
  # So gary opens. It is a turn like any other: streamed, stored, in the first
  # scene, and reaching the same engines — an opening that moves the party
  # somewhere records it, the same as any other turn would.
  #
  # It is a turn with no player message, which is the only thing unusual about
  # it. There has to be one of those, because somebody has to speak first and
  # it is not the player.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"
    And I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"

  Scenario: Gary opens the scene once there is somebody to open it for
    Given I add "Bramble" the rogue
    When I ask gary to begin
    Then the turn should stream to completion
    And the transcript should hold 1 turn
    And the opening should be gary's

  Scenario: The opening streams, like anything else gary says
    Given I add "Bramble" the rogue
    When I ask gary to begin
    Then the narration should arrive in more than one piece

  # It is the module that says where a campaign starts, and the world already
  # holds that. An opening that began somewhere else would be gary contradicting
  # the world on the very first sentence.
  Scenario: Gary is told where the module starts
    Given I add "Bramble" the rogue
    When I ask gary to begin
    Then gary should have been told the module is "the-drowned-belfry"
    And the party should have been among what gary was sent

  # An opening that describes a place and stops is a postcard. What prompted
  # this: "there's nothing actionable — no premise at all, just a description
  # of the current location", and then, asked "why am I here?", gary handed
  # the question back to the player.
  #
  # Which it did because nothing had told it. A premise is a situation in the
  # world; a hook is why these people are standing in it tonight and what
  # they have been asked to do. The module knows, so the module says.
  Scenario: Gary is told why the party is here at all
    Given I add "Bramble" the rogue
    When I ask gary to begin
    Then gary should have been told what brought the party here

  Scenario: The opening belongs to the first scene
    Given I add "Bramble" the rogue
    When I ask gary to begin
    Then there should be 1 scene
    And the opening should belong to the open scene

  # The engines are not suspended because it is the first turn.
  Scenario: An opening that changes the world records it
    Given I add "Bramble" the rogue
    When I ask gary to begin with "the bell tolls [[remember bell-rings=3]]"
    Then the turn should stream to completion
    And the world should remember "bell-rings" as "3"

  # Twice would be two openings in the transcript, and the second would be
  # narrated to a table that had already started.
  Scenario: A campaign that has already begun does not begin again
    Given I add "Bramble" the rogue
    And gary has begun
    When I ask gary to begin
    Then the response status should be 409
    And the response code should be "already_begun"

  Scenario: A campaign somebody has already played does not begin either
    Given I add "Bramble" the rogue
    And I said "I push open the door"
    When I ask gary to begin
    Then the response status should be 409
    And the response code should be "already_begun"

  Scenario: There is nobody to open the scene for
    When I ask gary to begin
    Then the response status should be 409
    And the response code should be "no_party"

  Scenario: Opening somebody else's campaign
    Given another account has a campaign
    When I ask gary to begin theirs
    Then the response status should be 404

  Scenario: Opening without a session
    Given I add "Bramble" the rogue
    And I am signed out
    When I ask gary to begin
    Then the response status should be 401

  # A failed opening must leave the campaign openable. Half a turn stored here
  # is worse than elsewhere: it would make the campaign look begun, and nothing
  # would ever open it properly.
  Scenario: Gary falling over on the opening leaves it still to be opened
    Given I add "Bramble" the rogue
    When I ask gary to begin with "[[fail]]"
    Then the stream should carry an error
    And the transcript should hold 0 turns
    And the campaign should still be waiting to begin

  # The same refusal a turn gives, and the opening is the first thing anybody
  # reaches — so on a deployment whose secrets are not set, this is the one
  # that has to read properly.
  Scenario: Opening on a deployment that cannot reach a model
    Given I add "Bramble" the rogue
    And this deployment has no model key
    When I ask gary to begin
    Then the response status should be 503
    And the response code should be "gm_unavailable"
    And the transcript should hold 0 turns

  # Free, instant, and true before gary has said a word: what the adventure is
  # about, in the module's own words. The page can show a situation while the
  # opening is still being written.
  Scenario: A campaign carries the module's premise
    When I read that campaign
    Then the response status should be 200
    And the campaign should carry the module's premise
    And the campaign should say where it begins
    And the campaign should say it has not begun
