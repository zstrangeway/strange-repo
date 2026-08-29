Feature: Where an application got to
  As someone with thirty of these in flight
  I want each one's history and where it stands now
  So that I stop guessing whether I ever heard back from anybody

  # The log is append-only and the current status is a fold over it, rather
  # than a column that gets overwritten. It is the same choice gary makes with
  # levels: the thing on screen is a fact derived from what happened, not a
  # value somebody remembered to keep up to date.
  #
  # It also buys the part people actually want months later — "when did I
  # apply, and how long did they sit on it" — which a mutable status column
  # throws away every time it is written.
  #
  # A posting starts at `saved` the moment it is saved. There is no state
  # before it, and nothing has to be logged for a posting to have a status.

  Background:
    Given a scratch scout directory
    And I have saved a posting for "Staff Engineer" at "Orrery"

  # ------------------------------------------------------------ moving along

  Scenario: A posting starts out saved
    When I read that posting
    Then its status should be "saved"
    And its history should be one entry saying it was saved

  Scenario: Logging that I applied
    When I log that posting as "applied"
    Then its status should be "applied"
    And its history should end with "applied"
    And that entry should be stamped with when it happened

  Scenario: A note goes with the status
    When I log that posting as "applied" noting "referral from Ada"
    Then its status should be "applied"
    And that entry's note should be "referral from Ada"

  Scenario: The whole way through
    When I log that posting as "applied"
    And I log that posting as "screening"
    And I log that posting as "interview"
    And I log that posting as "offer"
    Then its status should be "offer"
    And its history should be "saved", "applied", "screening", "interview", "offer"

  # Nothing is ever rewritten, so a note added later is a new entry rather
  # than an edit of an old one. The old note stays true about the moment it
  # was written.
  Scenario: Adding a note without changing the status
    Given I have logged that posting as "interview"
    When I add the note "they asked about the Postgres migration"
    Then its status should still be "interview"
    And its history should end with that note

  # --------------------------------------------------------- how it can end

  Scenario: Rejected
    Given I have logged that posting as "interview"
    When I log that posting as "rejected" noting "went with an internal candidate"
    Then its status should be "rejected"

  # Ghosted is a status somebody sets themselves, deliberately, because they
  # have decided it is over. scout does not infer it from silence — it has no
  # business deciding on somebody's behalf that a company is done with them.
  Scenario: Ghosted
    Given I have logged that posting as "applied"
    When I log that posting as "ghosted" noting "six weeks, three emails"
    Then its status should be "ghosted"

  # And ghosted is not a grave. Recruiters resurface, and when one does the
  # log should be able to say so rather than making somebody start again.
  Scenario: Coming back from ghosted
    Given I have logged that posting as "ghosted"
    When I log that posting as "screening" noting "they emailed, four months later"
    Then its status should be "screening"
    And its history should still show it was ghosted

  # ------------------------------------------------------ what it will not do

  # The path is enforced because the mistake it catches is a real one: logging
  # "offer" on the wrong posting out of a list of thirty. Refusing it and
  # saying what would be allowed is what makes the slip visible at the moment
  # it happens, rather than in a status report weeks later.
  Scenario: Skipping the middle
    When I log that posting as "offer"
    Then scout should refuse it
    And scout should say what I can log from "saved"

  Scenario: Going backwards
    Given I have logged that posting as "interview"
    When I log that posting as "applied"
    Then scout should refuse it
    And scout should say what I can log from "interview"

  Scenario: A status that is not one of the seven
    When I log that posting as "vibing"
    Then scout should refuse it
    And scout should list the statuses there are

  Scenario: Logging against a posting that is not there
    When I log a posting that does not exist as "applied"
    Then scout should refuse it
    And scout should say no such posting

  # -------------------------------------------------------------- reading it

  Scenario: Seeing everything in flight
    Given I have saved a posting for "Platform Lead" at "Thornfield"
    And I have logged that posting as "applied"
    When I list my postings
    Then each one should show its status
    And each one should show when it last moved

  Scenario: Seeing only what is still alive
    Given I have logged that posting as "rejected"
    And I have saved a posting for "Platform Lead" at "Thornfield"
    When I list the postings still in play
    Then "Platform Lead" should be listed
    And "Staff Engineer" should not be listed
