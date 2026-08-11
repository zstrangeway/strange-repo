Feature: Scenes
  As someone playing a campaign over many sittings
  I want play divided into scenes
  So that gary's memory stays sharp and the campaign stays affordable

  # A scene is a bounded stretch of play, and it does two jobs that are really
  # the same job.
  #
  # It bounds the context. Today every turn sends the whole transcript, so a
  # campaign costs more per turn the longer it runs, without limit. A scene is
  # what the transcript means: gary is told this scene's turns and the recaps
  # of the ones before it, not every word since the first.
  #
  # And it is where the world is reconciled. Prose stops being memory at a
  # scene boundary — after it, what gary knows is the world as the event log
  # has it, plus the recaps. So the boundary is the last moment at which
  # something narrated but never recorded can still be recorded, and closing a
  # scene asks gary for exactly that. It is not a licence to assert: what it
  # proposes goes through the same engines, with the same refusals, and lands
  # in the same history.
  #
  # Who decides where a scene ends: gary may ask, the player may say, and the
  # engine breaks one that has run long whatever either of them thinks. That
  # last part is the point. A bound the model can decline to apply is not a
  # bound, and "how much does a turn cost" is not a narrative judgement.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"
    And I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    And I add "Bramble" the rogue

  Scenario: A campaign begins in its first scene
    When I read the scenes
    Then the response status should be 200
    And there should be 1 scene
    And the scene should be open

  # The whole reason scenes exist. Without this the rest is bookkeeping.
  Scenario: Gary is told this scene's turns, not the campaign's
    Given I said "I push open the door"
    And a new scene begins
    And I said "I climb the stair"
    When I say "What was I doing"
    Then gary should have been sent 3 prior turns

  Scenario: Gary is told what happened in the scenes before this one
    Given I said "I push open the door"
    And a new scene begins
    When I say "Where was I"
    Then the recap of the first scene should have been among what gary was sent

  # The world does not reset at a boundary. It is the thing that survives one.
  Scenario: A scene break does not lose the world
    Given I said "I climb the stair [[move the belfry stair]]"
    And I said "The step gives way [[damage Bramble 4]]"
    When a new scene begins
    Then the world should say the party is at "the belfry stair"
    And the world should have "Bramble" 4 hit points down

  Scenario: Starting a scene by hand
    Given I said "I push open the door"
    When I begin a scene called "The flooded nave"
    Then the response status should be 201
    And there should be 2 scenes
    And the open scene should be called "The flooded nave"

  Scenario: A scene needs somebody at the table
    Given I started "An empty table" on "dnd-5e" running "the-drowned-belfry"
    When I begin a scene in that campaign
    Then the response status should be 409
    And the response code should be "no_party"

  Scenario: Somebody else's scenes
    Given another account has a campaign
    When I read their scenes
    Then the response status should be 404

  # Gary asks; the engine acts, and acts after the turn rather than in the
  # middle of it. A boundary inside a turn would leave that turn's narration
  # half in one scene and half in the next, and the turn that ends a scene is
  # the last turn of it.
  Scenario: Gary asks for a new scene, and gets one when the turn is over
    When I say "You travel three days north [[scene The road to Ashfen]]"
    Then the turn should stream to completion
    And the stream should carry a scene change
    And there should be 2 scenes
    And the open scene should be called "The road to Ashfen"
    And gary's turn should belong to the first scene

  # The bound is the engine's, not gary's. A model that never asks for a scene
  # break is exactly the model this protects against.
  Scenario: A scene that has run long is broken whether gary asks or not
    Given a scene is broken after 4 turns
    And I said "One"
    And I said "Two"
    When I say "Three"
    Then there should be 2 scenes
    And gary should have been sent 1 prior turn

  # Turns are a poor proxy for cost when they are long, so length counts too.
  Scenario: A scene too big to send is broken on its size
    Given a scene is broken after 100 characters
    And I said "A very long speech indeed, at some length"
    When I say "And another one, equally long and unhurried"
    Then there should be 2 scenes

  Scenario: The scene a turn belonged to comes back with it
    Given I said "I push open the door"
    And a new scene begins
    And I said "I climb the stair"
    When I read the transcript
    Then the turns should carry the scene they happened in
    And the transcript should read back 2 scenes

  # ------------------------------------------------------- reconciling

  Scenario: Closing a scene records what happened in it
    Given I said "I push open the door"
    When a new scene begins
    Then the first scene should be closed
    And the first scene should have a recap

  # The last moment this is possible. After the boundary the prose is gone and
  # a fact nobody recorded is a fact nobody can recover.
  Scenario: Something narrated but never recorded is recorded at the boundary
    Given gary will remember "brass-key" as "in Bramble's pocket" when the scene closes
    And I said "You pocket the brass key"
    When a new scene begins
    Then the world should remember "brass-key" as "in Bramble's pocket"

  # Reconciling is not a licence to assert. It is one more pass through the
  # same gates, and the gates do not soften because the scene is ending.
  Scenario: Reconciling cannot do what a turn could not
    Given gary will hurt "Nobody" when the scene closes
    And I said "Something bites at the dark"
    When a new scene begins
    Then the world should have "Bramble" at full hit points
    And there should be 2 scenes

  # No dice after the fact. A die thrown once the scene is over would decide
  # something nobody was at the table for, so the close pass is not offered
  # one — and is refused if it asks anyway.
  Scenario: Reconciling cannot roll dice
    Given gary will roll dice when the scene closes
    And I said "I search the room"
    When a new scene begins
    Then no roll should have been recorded
    And there should be 2 scenes
    And the first scene should have a recap

  Scenario: What reconciling changed is in the history, against the scene
    Given gary will remember "brass-key" as "in Bramble's pocket" when the scene closes
    And I said "You pocket the brass key"
    When a new scene begins
    Then the history should hold that change against the first scene

  # Losing a recap is bad. Failing to close is worse: the context would go on
  # growing, which is the thing scenes exist to stop.
  Scenario: A scene closes even when gary cannot say what happened in it
    Given gary is unreachable when the scene closes
    And I said "I push open the door"
    When a new scene begins
    Then there should be 2 scenes
    And the first scene should be closed
    And the first scene should say its recap is missing

  # Recapping is summarising, not running a game. It is the one call here that
  # does not need the model the campaign chose, and a scene break is otherwise
  # the most expensive moment in a campaign.
  Scenario: Recapping runs on the cheap model, not the campaign's
    Given I said "I push open the door"
    When a new scene begins
    Then the recap should have been asked of the scene model
    And the scene model should not be the campaign's model

  Scenario: A scene with nothing in it needs no reconciling
    When I begin a scene called "The flooded nave"
    Then the response status should be 201
    And gary should not have been asked to close anything
