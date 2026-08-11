Feature: Playing
  As someone with a character in a campaign
  I want to say what I do and have gary answer
  So that there is a game rather than a form

  # Gary is stood in for here, exactly as Google and Facebook are. The double
  # reads what to do out of the player's message rather than holding state a
  # scenario arranged first, so a scenario says what gary does at the moment
  # it sends the message, and two scenarios can never leak into each other.
  # The directives are spec-only and never reach what is stored.
  #
  # Dice are gary's to ask for and never gary's to invent. A language model
  # asked for a number gives a plausible one, which is precisely the wrong
  # thing when the number decides what happens. The roll is a tool call the
  # API answers from its own generator, so what a spec asserts is a roll that
  # really happened.
  #
  # A turn streams. That is the whole reason the failures below are events on
  # an open stream rather than statuses: once the first byte is out the status
  # is spent, and a refusal that arrives as a dropped connection reads as gary
  # being broken rather than gary declining.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"
    And I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    And I add "Bramble" the rogue

  Scenario: Saying what I do, and being answered
    When I say "I push open the door"
    Then the turn should stream to completion
    And the narration should mention "door"
    And the transcript should hold 2 turns

  # More than one narration event, or it is not streaming — it is a whole
  # response through a stream-shaped hole, which is what this exists to catch.
  Scenario: The narration arrives in pieces
    When I say "I push open the door"
    Then the narration should arrive in more than one piece

  Scenario: Gary asks for a roll, and the API rolls it
    When I say "I search the room [[roll 1d20+3 Perception]]"
    Then the turn should stream to completion
    And a roll of "1d20+3" should have been made for "Perception"
    And the roll should be recorded against gary's turn
    And narration should arrive after the roll

  Scenario: A roll stays inside what its notation allows
    When I say "I search the room [[roll 1d20+3 Perception]]"
    Then the roll total should be between 4 and 23

  # The seed is what makes the number assertable at all. Without it this spec
  # could only say a number arrived, which is what it would say if gary had
  # made one up.
  Scenario: The same seed rolls the same dice
    Given the dice are seeded with 7
    When I say "I search the room [[roll 1d20+3 Perception]]"
    And the dice are seeded with 7 again
    And I say "I search the room [[roll 1d20+3 Perception]]"
    Then both rolls should have the same total

  Scenario: Notation gary cannot roll
    When I say "I search the room [[roll 1d20+lots Perception]]"
    Then the stream should carry an error
    And no roll should have been recorded

  # What gary is told next time is the transcript, which is why it is stored
  # before the stream opens rather than after it closes.
  Scenario: The transcript is what gary is told next time
    Given I said "I am called Bramble"
    When I say "What is my name"
    Then gary should have been sent 3 prior turns
    And the party should have been among what gary was sent

  Scenario: The module is what gary is playing
    When I say "Where am I"
    Then gary should have been told the module is "the-drowned-belfry"
    And gary should have been told the system is "dnd-5e"

  Scenario: Playing someone else's campaign
    Given another account has a campaign
    When I say "I push open the door" in their campaign
    Then the response status should be 404

  Scenario: Playing without a session
    Given I am signed out
    When I say "I push open the door"
    Then the response status should be 401

  Scenario: Saying nothing
    When I say "   "
    Then the response status should be 422

  # A campaign nobody is in has nothing for gary to narrate about.
  Scenario: Playing before there is anybody to play
    Given I started "An empty table" on "dnd-5e" running "the-drowned-belfry"
    When I say "I push open the door" in that campaign
    Then the response status should be 409
    And the response code should be "no_party"

  Scenario: Gary declines to narrate something
    When I say "I do something unspeakable [[refuse]]"
    Then the stream should carry a refusal
    And the refusal should say why in words
    And the transcript should hold 1 turn

  Scenario: Gary is unreachable
    When I say "I push open the door [[fail]]"
    Then the stream should carry an error
    And the transcript should hold 1 turn

  # A turn cut off halfway is kept and marked, not silently dropped. Dropping
  # it would leave the next turn being told a story that never happened; and
  # keeping it unmarked would claim gary finished a sentence it did not.
  #
  # Driven through the endpoint rather than through the test client, which
  # cannot do this one: its transport has no backpressure, so a reader that
  # walks away does not stop the writer and the turn runs forever. The
  # endpoint, its generator and the clause that marks the turn are all the
  # real ones — only the socket is missing, and the socket is the part that
  # cannot be faked.
  Scenario: A turn cut off halfway is kept and marked
    When gary is interrupted halfway through "I push open the door [[stall]]"
    Then the transcript should hold 2 turns
    And gary's turn should be marked incomplete

  # A deployment with no key is a real state, not a hypothetical one: it is
  # what a fresh Fly app is until its secrets are set. It has to read as gary
  # not being configured rather than as gary crashing, and it has to be
  # refused before the stream opens — after that there is no status left to
  # say it with.
  Scenario: Playing on a deployment that cannot reach a model
    Given this deployment has no model key
    When I say "I push open the door"
    Then the response status should be 503
    And the response code should be "gm_unavailable"
    And the transcript should hold 0 turns

  Scenario: A campaign that does not exist
    When I say "I push open the door" in a campaign that does not exist
    Then the response status should be 404

  # The rules grade a check; gary does not. This is the difference between a
  # GM bound by a system and a GM describing one.
  Scenario: The rules grade the check
    When I say "I search the room [[check Bramble 15 Perception]]"
    Then the turn should stream to completion
    And the check should have been recorded against 15
    And the degree should be one this system grades

  # Same tool, same narrator, a system that grades four ways instead of two —
  # and nothing between them knows the difference.
  Scenario: A system that grades four ways grades four ways
    Given I started "Salt in the wind" on "pathfinder-2e" running "salt-and-cinder"
    And I add "Ket" the rogue
    When I say "I search the quay [[check Ket 15 Perception]]"
    Then the turn should stream to completion
    And the degree should be one this system grades
    And this system should grade 4 ways

  Scenario: Gary moves the party, and the world keeps them moved
    When I say "I climb the stair [[move the belfry stair]]"
    Then the turn should stream to completion
    And the world should say the party is at "the belfry stair"

  Scenario: Gary remembers something, and it outlives the turn
    When I say "The bell rings again [[remember bell-rings=4]]"
    Then the turn should stream to completion
    And the world should remember "bell-rings" as "4"

  Scenario: Gary takes hit points off, and the world keeps them off
    When I say "The step gives way [[damage Bramble 4]]"
    Then the turn should stream to completion
    And the world should have "Bramble" 4 hit points down

  # The engine refusing the model is the point of having an engine. Gary
  # cannot hurt somebody who is not at the table, however plausibly it narrates.
  Scenario: Gary cannot touch somebody who is not here
    When I say "Something bites [[damage Nobody 4]]"
    Then the stream should carry an error
    And the world should have "Bramble" at full hit points

  Scenario: What gary changed is in the history, against the turn that did it
    When I say "I climb the stair [[move the belfry stair]]"
    Then the turn should stream to completion
    And the move should be recorded against gary's turn

  Scenario: Gary marks a condition, and the world holds it
    When I say "The shape turns to face you [[afflict Bramble frightened]]"
    Then the turn should stream to completion
    And the world should have "Bramble" "frightened"

  Scenario: Gary lets time pass, and the world counts it
    When I say "You rest a while [[time 30]]"
    Then the turn should stream to completion
    And the world should say 30 minutes have passed

  Scenario: A check gary cannot grade
    When I say "I look about [[check Bramble hard Perception]]"
    Then the stream should carry an error
    And no roll should have been recorded

  # A client that reloads mid-campaign has to get the table back, and the
  # stream only carries what happens next.
  # Reported from a real session: seven rolls landed, two people lost hit
  # points, and gary never got to say what happened — it spent the whole turn
  # calling tools and ran out of rounds. The turn was then deleted for having
  # no prose, which took its rolls with it (they cascade) and left the damage
  # behind (world events do not). A refresh showed a story where nothing
  # happened, beside a party that was bleeding.
  #
  # A turn is only nothing if it did nothing. Silence is not nothing.
  Scenario: A turn that did things but said nothing is still a turn
    Given I said "we cross the planks [[check Bramble 12 avoid collapse]] [[damage Bramble 5]] [[mute]]"
    When I read the transcript
    Then the transcript should read back 2 turns
    And gary's turn should carry a roll of "1d20"
    And the world should have "Bramble" 5 hit points down

  Scenario: Reading the transcript back
    Given I said "I push open the door"
    When I read the transcript
    Then the response status should be 200
    And the transcript should read back 2 turns
    And the first turn should be mine

  Scenario: A roll comes back beside the turn it happened in
    Given I said "I search the room [[roll 1d20+3 Perception]]"
    When I read the transcript
    Then gary's turn should carry a roll of "1d20+3"

  Scenario: Someone else's transcript
    Given another account has a campaign
    When I read their transcript
    Then the response status should be 404
