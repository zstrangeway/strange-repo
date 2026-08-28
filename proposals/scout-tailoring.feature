Feature: Tailoring a resume to a posting
  As someone whose master resume is four pages of everything I have ever done
  I want a version of it aimed at one posting
  So that the reader sees the relevant half first, and I still recognise it

  # The whole design of this feature is one constraint: tailoring may reorder,
  # reweight and rephrase what the master resume already says, and may not add
  # anything to it. A resume that claims Kubernetes because the posting asked
  # for Kubernetes is a lie told in the applicant's name, and it is a lie they
  # will not find out about until somebody asks them about it out loud.
  #
  # So the model's output is not trusted. Every draft it returns is checked
  # against the master's own vocabulary — the employers it names and the
  # skills it claims — before a single byte reaches the disk. A draft that
  # introduces either is rejected whole; nothing partial is ever written.
  #
  # That check is deterministic and lives in scout, not in the prompt. A
  # prompt is a request. This is the part that holds when the model ignores it,
  # which is the only reason to have it at all.
  #
  # No spec here calls a real model. The provider is stubbed, exactly as
  # gary-api stubs its narrator, and `task scout:smoke` is the opt-in command
  # that spends real tokens against a real Anthropic key.

  Background:
    Given a scratch scout directory
    And a master resume naming "Wilding Labs" and "Thornfield Systems"
    And the master resume claiming "Python", "Postgres" and "Terraform"
    And I have saved a posting for "Staff Engineer" at "Orrery"

  # --------------------------------------------------------- what it writes

  Scenario: Tailoring writes a versioned file beside the master
    Given the model will return a draft drawn only from the master
    When I tailor my resume for that posting
    Then a resume should be written for that posting at version 1
    And the master resume should be unchanged

  # Versions accumulate rather than overwrite. The reason is that the second
  # attempt is usually not better than the first, and the first is gone by the
  # time anybody notices.
  Scenario: Tailoring again keeps the one before it
    Given I have already tailored my resume for that posting
    And the model will return a different draft drawn only from the master
    When I tailor my resume for that posting
    Then a resume should be written for that posting at version 2
    And version 1 should still say what it said

  # The summary is the point of the feature as much as the file is: it is how
  # somebody decides whether to send it without diffing four pages by eye.
  Scenario: Tailoring says what it changed
    Given the model will return a draft drawn only from the master
    When I tailor my resume for that posting
    Then scout should summarise what changed
    And the summary should name what it moved up
    And the summary should name what it played down

  # ------------------------------------------------- the check that matters

  # The single most important scenario in scout. If this one passes while the
  # implementation is wrong, the feature is worse than not having been built.
  Scenario: A draft that names an employer I never worked for
    Given the model will return a draft naming "Initech" as an employer
    When I tailor my resume for that posting
    Then scout should refuse the draft
    And scout should say "Initech" is not in the master resume
    And no resume file should have been written

  Scenario: A draft that claims a skill I never claimed
    Given the model will return a draft claiming "Kubernetes"
    When I tailor my resume for that posting
    Then scout should refuse the draft
    And scout should say "Kubernetes" is not in the master resume
    And no resume file should have been written

  # The complement, and just as necessary: a check that rejects everything is
  # trivially safe and useless. Moving Terraform to the top because the
  # posting asks for it is the entire job.
  Scenario: A draft that only reorders what the master already said
    Given the model will return a draft leading with "Terraform" and "Postgres"
    When I tailor my resume for that posting
    Then the draft should be accepted
    And the tailored resume should lead with "Terraform"

  Scenario: A draft that rephrases without adding
    Given the model will return a draft rephrasing my Wilding Labs work
    When I tailor my resume for that posting
    Then the draft should be accepted

  # A rejection is not a dead end. Rejecting and saying nothing is how a
  # person concludes the tool is broken rather than that the draft was.
  Scenario: A refused draft is still readable
    Given the model will return a draft claiming "Kubernetes"
    When I tailor my resume for that posting
    Then scout should show me the draft it refused
    And scout should tell me I can tailor again

  # ------------------------------------------------------- when it can't go

  Scenario: No master resume to tailor from
    Given there is no master resume
    When I tailor my resume for that posting
    Then scout should refuse it
    And scout should say where it looked for the master resume

  Scenario: An empty master resume
    Given the master resume is empty
    When I tailor my resume for that posting
    Then scout should refuse it
    And scout should say the master resume had nothing in it

  # The key is the user's own and lives in their environment. scout never
  # stores it, never logs it, and says so plainly when it is missing rather
  # than failing somewhere inside an HTTP client.
  Scenario: No API key set
    Given no Anthropic API key is set
    When I tailor my resume for that posting
    Then scout should refuse it
    And scout should name the variable it expects

  Scenario: The model refuses or errors
    Given the model will fail
    When I tailor my resume for that posting
    Then scout should refuse it
    And scout should say the model call failed
    And no resume file should have been written

  Scenario: Tailoring for a posting that is not there
    When I tailor my resume for a posting that does not exist
    Then scout should refuse it
    And scout should say no such posting
