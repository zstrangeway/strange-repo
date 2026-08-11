Feature: The world
  As someone playing a long campaign
  I want gary to know what is true rather than remember what it said
  So that the story does not drift out from under me

  # This is the answer to the way these things usually fail. A chatbot GM's
  # only memory is its own prose, so the tenth turn contradicts the second and
  # nobody can say which one was right. Here the transcript is prose and the
  # world is state, and they are different things.
  #
  # The world is an append-only log, projected on read. Nothing overwrites: a
  # character on 3 hit points is on 3 hit points because of a list of things
  # that happened, and that list is still there to read. There is no snapshot
  # column to disagree with the log, because there is no snapshot column.
  #
  # The model proposes changes and never asserts them. Everything below is
  # reachable without a model at all, which is the point — it is code, and it
  # can be pinned down exactly.

  Background:
    Given I am signed in at google as "ada@example.com" named "Ada Lovelace"
    And I started "A Light in the Deep" on "dnd-5e" running "the-drowned-belfry"
    And I add "Bramble" the rogue

  Scenario: A new campaign starts somewhere
    When I read the world
    Then the response status should be 200
    And the party should be somewhere
    And no time should have passed
    And nothing should be remembered yet

  Scenario: The party moves, and stays moved
    When the party moves to "the belfry stair"
    And I read the world
    Then the party should be at "the belfry stair"

  Scenario: Only the latest move counts
    Given the party moves to "the belfry stair"
    When the party moves to "the flooded nave"
    And I read the world
    Then the party should be at "the flooded nave"

  Scenario: A fact is remembered
    When gary remembers "bell-rings" as "3"
    And I read the world
    Then "bell-rings" should be remembered as "3"

  Scenario: A fact is corrected rather than duplicated
    Given gary remembers "bell-rings" as "3"
    When gary remembers "bell-rings" as "4"
    And I read the world
    Then "bell-rings" should be remembered as "4"
    And 1 fact should be remembered

  Scenario: Time passes and accumulates
    When 30 minutes pass
    And 45 minutes pass
    And I read the world
    Then 75 minutes should have passed

  Scenario: A character takes damage
    When "Bramble" takes 4 damage
    And I read the world
    Then "Bramble" should be 4 hit points down

  Scenario: Damage accumulates rather than replacing
    Given "Bramble" takes 4 damage
    When "Bramble" takes 3 damage
    And I read the world
    Then "Bramble" should be 7 hit points down

  Scenario: Healing gives it back
    Given "Bramble" takes 6 damage
    When "Bramble" heals 4
    And I read the world
    Then "Bramble" should be 2 hit points down

  # Being healed past full is common and is not an error; it just does not
  # make anyone tougher than they are.
  Scenario: Healing stops at full
    Given "Bramble" takes 2 damage
    When "Bramble" heals 10
    And I read the world
    Then "Bramble" should be at full hit points

  Scenario: Damage stops at nothing
    When "Bramble" takes 500 damage
    And I read the world
    Then "Bramble" should be on 0 hit points
    And "Bramble" should be down

  Scenario: A condition is taken on and shaken off
    When "Bramble" becomes "frightened"
    And I read the world
    Then "Bramble" should be "frightened"
    When "Bramble" stops being "frightened"
    And I read the world
    Then "Bramble" should not be "frightened"

  Scenario: The same condition twice is still one condition
    Given "Bramble" becomes "frightened"
    When "Bramble" becomes "frightened"
    And I read the world
    Then "Bramble" should have 1 condition

  # The log is the point. A state anyone can overwrite is a state nobody can
  # explain, and "why does gary think that" is the question this exists to
  # answer.
  Scenario: Everything that happened is still there to read
    Given the party moves to "the belfry stair"
    And "Bramble" takes 4 damage
    And 30 minutes pass
    When I read what has happened
    Then the response status should be 200
    And 3 things should have happened
    And they should be in the order they happened

  Scenario: Someone else's world is not mine to read
    Given another account has a campaign
    When I read their world
    Then the response status should be 404

  Scenario: Reading the world needs a session
    Given I am signed out
    When I read the world
    Then the response status should be 401
