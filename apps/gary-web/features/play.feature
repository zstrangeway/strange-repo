Feature: Playing at the table
  As someone with a character in a campaign
  I want to say what I do and watch gary answer
  So that it reads like a game rather than a form submission

  # This is the half of streaming a spec can actually see. gary-api's own
  # specs prove the frames are sent; these prove a browser renders them as
  # they arrive rather than all at once at the end.
  #
  # The session is a bearer token in localStorage, so EventSource is not an
  # option — it cannot set an Authorization header. The client is fetch and a
  # ReadableStream, which is why the frame parsing is a plain module under
  # src/lib and covered there rather than only here.

  Background:
    Given I have signed in at google as "ada@example.com" named "Ada"
    And I already have a campaign called "A Light in the Deep"
    And "Bramble" the rogue is at the table

  Scenario: Saying what I do, and being answered
    When I open that campaign
    And I say "I push open the door"
    Then the transcript should show what I said
    And gary should answer

  Scenario: The narration arrives before the turn is over
    When I open that campaign
    And I say "I take my time about it"
    Then the narration should appear while it is still being written

  # A roll is a thing that happened, not a sentence gary wrote. Rendering it
  # as prose would make it indistinguishable from a number gary made up,
  # which is the distinction the whole design rests on.
  Scenario: A roll shows as a roll, not as prose
    When I open that campaign
    And I say "I search the room" and gary rolls
    Then the transcript should show a roll of "1d20+3"
    And the roll should show its total

  Scenario: I cannot talk over gary
    When I open that campaign
    And I say "I push open the door"
    Then I should not be able to say anything while gary is answering

  Scenario: The composer comes back when the turn ends
    When I open that campaign
    And I say "I push open the door"
    And gary finishes
    Then I should be able to say something again

  # An error after the first byte cannot be a status, so it arrives in the
  # stream. It has to read as gary having a problem rather than the page
  # being broken, and what was already narrated has to stay.
  Scenario: A failure mid-turn leaves the transcript honest
    When I open that campaign
    And I say "I push open the door" and gary falls over
    Then the transcript should still show what I said
    And the page shows an error about gary

  Scenario: Gary declining reads as gary declining
    When I open that campaign
    And I say "something unspeakable" and gary declines
    Then the page shows that gary declined
    And I should be able to say something again

  Scenario: The party is on screen while playing
    When I open that campaign
    Then the page shows "Bramble"
    And the page shows "8/8"

  Scenario: The transcript survives a reload
    When I open that campaign
    And I say "I push open the door"
    And gary finishes
    And I reload the page
    Then the transcript should show what I said

  # Switching to something cheap mid-session should not mean going back to a
  # settings page.
  Scenario: Changing the model without leaving the table
    When I open that campaign
    Then the page shows which model is running it
    When I move it to "Claude Haiku 4.5"
    Then the page shows which model is running it
    And the page shows "Claude Haiku 4.5"

  # A scene divides the table the way it divides gary's memory: what is on
  # screen above a boundary is the story so far, and what gary is actually
  # working from is below it. Showing the two as one undivided scroll would
  # hide the most consequential thing about a long campaign.
  Scenario: A scene break shows on the table
    When I open that campaign
    And I say "I push open the door"
    And gary finishes
    And I start a new scene called "The flooded nave"
    Then the transcript should show a break for "The flooded nave"
    And the page shows what happened in the scene before

  Scenario: Gary asking for a scene shows the same break
    When I open that campaign
    And I say "You travel three days north" and gary changes scene
    And gary finishes
    Then the transcript should show a break for "The road to Ashfen"
