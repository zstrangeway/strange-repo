Feature: Saving a posting
  As someone applying to a lot of places
  I want a posting kept whole the moment I find it
  So that tailoring and the status log have something durable to hang off

  # A posting is the first thing in scout that belongs to somebody. A tailored
  # resume and an application's history both hang off one, and reaching either
  # means reaching the posting first.
  #
  # Everything here is local: the row is in a SQLite file under the working
  # directory and the text came from this machine's own fetch. Nothing is sent
  # anywhere at save time — the model is not involved until tailoring asks for
  # it, which is why saving works with no API key at all.

  Background:
    Given a scratch scout directory

  # ------------------------------------------------------------ pasted text

  # Pasting is the path that always works, and the one the README leads with.
  # No board can block it and no extractor can misread it.
  Scenario: Saving a posting I pasted
    When I save a posting pasted as:
      """
      Senior Platform Engineer at Wilding Labs
      We are looking for someone with deep Postgres and Python experience.
      """
    Then the posting should be saved
    And the posting text should mention "deep Postgres"
    And scout should tell me the posting's reference

  Scenario: Naming the role and company myself
    When I save that pasted posting as "Senior Platform Engineer" at "Wilding Labs"
    Then the posting's title should be "Senior Platform Engineer"
    And the posting's company should be "Wilding Labs"

  # scout guesses a title from what the page said about itself, and never
  # guesses a company. A wrong company is worse than a blank one: it is the
  # field somebody reads back weeks later to remember who they wrote to, and
  # a plausible guess is indistinguishable from a fact once it is in the row.
  Scenario: A posting whose company nobody supplied
    When I save that pasted posting with no title or company
    Then the posting's company should be recorded as unknown
    And scout should say the company is unknown and how to set it

  Scenario: A posting with no text in it at all
    When I save a posting pasted as "   "
    Then scout should refuse it
    And scout should say the posting was empty

  # ------------------------------------------------------------------- URLs

  Scenario: Saving a posting from a URL
    Given a job board serving a posting for "Staff Engineer" at "Wilding Labs"
    When I save a posting from that URL
    Then the posting should be saved
    And the posting's source URL should be that URL
    And the posting text should be the readable part of the page
    And the posting text should not contain the page's navigation

  # trafilatura returns the article and drops the chrome. What it cannot do is
  # invent an article that a login wall or a JavaScript shell never served —
  # and a posting saved as a cookie banner is worse than one never saved,
  # because tailoring will happily read it and produce something confident.
  Scenario: A board that serves a shell and fills it in with JavaScript
    Given a job board that serves an empty JavaScript shell
    When I save a posting from that URL
    Then scout should refuse it
    And scout should say the page had no readable posting in it
    And scout should tell me to paste the text instead

  Scenario: A board that refuses the fetch
    Given a job board that answers 403
    When I save a posting from that URL
    Then scout should refuse it
    And scout should say the board refused the fetch
    And scout should tell me to paste the text instead

  Scenario: A URL that never answers
    Given a job board that never answers
    When I save a posting from that URL
    Then scout should refuse it
    And scout should say the fetch timed out

  # Applying twice to the same posting is a thing people do by accident, and
  # the second save is nearly always a mistake rather than an intent. Refusing
  # it and naming the first one is what makes it visible.
  Scenario: Saving a URL I have already saved
    Given a job board serving a posting for "Staff Engineer" at "Wilding Labs"
    And I have saved a posting from that URL
    When I save a posting from that URL again
    Then scout should refuse it
    And scout should name the posting I already have

  # ---------------------------------------------------------------- reading

  Scenario: Listing what I have saved, newest first
    Given I have saved a posting for "Staff Engineer" at "Wilding Labs"
    And I have saved a posting for "Platform Lead" at "Thornfield"
    When I list my postings
    Then the postings should be "Platform Lead", "Staff Engineer"
    And each one should show its status

  Scenario: Reading one posting back
    Given I have saved a posting for "Staff Engineer" at "Wilding Labs"
    When I read that posting
    Then the posting's title should be "Staff Engineer"
    And the posting text should be the whole text as saved
