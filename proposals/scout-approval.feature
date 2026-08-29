Feature: Approving what is about to be sent
  As someone letting Claude apply to jobs on my behalf
  I want to see everything that will be submitted, and what was actually checked
  So that approving is diligence rather than a rubber stamp

  # This is the step the whole product turns on, and the easiest one to build
  # badly. If approving means reading a four-page resume every time, tailoring
  # saved nobody anything — writing was swapped for proofreading. If it means
  # glancing and clicking yes, the approval is theatre, and whatever the model
  # invented goes out under somebody's name to a company they want to work for.
  #
  # So the artifact is the product surface, not a report bolted onto one.
  #
  # ---------------------------------------------------------------------------
  #
  # The rule that shapes everything here: **approval scope and check scope are
  # different, and only one of them is hard.**
  #
  # `grounding.py` can speak to a tailored resume, because a tailored resume is
  # a projection of the master and "did anything new appear" is a well-formed
  # question about it. It cannot speak to "why do you want to work here" — that
  # is genuine new composition, and refusing it would be wrong.
  #
  # That does not have to be solved to be safe. A package shows **everything**
  # about to be submitted; the check covers the part it can honestly speak to;
  # and the package says which part that was. Somebody can approve text nothing
  # verified, as long as they were actually shown it and told it was unverified.
  #
  # The failure this exists to prevent is not "unchecked text" — it is unchecked
  # text presented as though something had checked it.
  #
  # ⚠️ scout does not submit anything, and is not going to. The browser belongs
  # to whatever agent is driving — it has the user's own logged-in sessions, and
  # scout has no business growing a second one. scout's job ends at an approved
  # package; sending it is somebody else's, and `applied` is then logged like
  # any other status.

  Background:
    Given a scratch scout directory
    And a master resume naming "Wilding Labs" and "Thornfield Systems"
    And I have saved a posting for "Staff Engineer" at "Orrery"
    And I have tailored my resume for that posting

  # ------------------------------------------------------- what is in a package

  Scenario: A package is everything about to be sent
    When I assemble a package for that posting
    Then the package should include the tailored resume at version 1
    And the package should say what changed in that resume

  # Whatever wrote this — Claude, or the person — scout did not, and scout has
  # no opinion about whether it is any good. It is in the package because it is
  # going to be submitted, and that is the only test for inclusion.
  Scenario: Text somebody else wrote goes in too
    Given I have assembled a package for that posting
    When I add the answer "Why do you want to work here?" to that package
    Then the package should include that answer in full
    And the package should include the tailored resume as well

  Scenario: An empty answer is not an answer
    Given I have assembled a package for that posting
    When I add the answer "Why do you want to work here?" with nothing in it
    Then scout should refuse it

  # ------------------------------------------------------------ what it claims

  Scenario: It says which parts were checked
    Given I have assembled a package for that posting
    And I have added an answer to that package
    When I read that package
    Then the resume should be marked as checked against the master resume
    And the answer should be marked as not checked

  # The honesty rule, as its own scenario because it is the one thing here that
  # cannot be allowed to drift. A package that reads as a clean bill of health
  # for text nothing examined is worse than no package at all: it converts a
  # person's caution into confidence and is wrong to.
  Scenario: It never implies it checked more than it did
    Given I have assembled a package for that posting
    And I have added an answer to that package
    When I read that package
    Then the package should say in words that not everything in it was checked
    And the package should say what the check does not cover

  Scenario: A package where everything happens to be checkable
    Given I have assembled a package for that posting
    When I read that package
    Then the package should say the whole of it was checked

  # There is no package around a resume that was refused, because there is no
  # resume — tailoring writes nothing when the check fails. Assembling one
  # anyway would mean a package whose main document does not exist.
  Scenario: Nothing to approve when the resume was refused
    Given I have saved a posting for "Platform Lead" at "Thornfield"
    And the model will return a draft claiming "Kubernetes"
    When I tailor my resume for that posting
    And I assemble a package for that posting
    Then scout should refuse it
    And scout should say there is no tailored resume for that posting yet

  # ---------------------------------------------------------------- approving

  Scenario: Approving records the decision
    Given I have assembled a package for that posting
    When I approve that package
    Then the package should be approved
    And its history should show when it was approved

  # The load-bearing scenario in this file. Without it, "approved" is a flag on
  # a posting rather than a statement about particular words, and the flow that
  # breaks is the obvious one: a package is approved, something regenerates the
  # resume, and what gets submitted is not what anybody said yes to. Nobody
  # would ever find out.
  Scenario: Approval is of these exact words, not of this posting
    Given I have approved a package for that posting
    When I tailor my resume for that posting again
    Then that package should no longer be approved
    And scout should say the resume changed after it was approved

  Scenario: Changing an answer withdraws approval too
    Given I have approved a package for that posting
    When I change an answer in that package
    Then that package should no longer be approved
    And scout should say what changed after it was approved

  Scenario: Adding an answer withdraws approval
    Given I have approved a package for that posting
    When I add the answer "Anything else?" to that package
    Then that package should no longer be approved

  # Approving again after a change is how somebody says yes to the new version.
  Scenario: Approving again after a change
    Given I have approved a package for that posting
    And I have changed an answer in that package
    When I approve that package
    Then the package should be approved

  Scenario: Approving a package that is not there
    When I approve a package for a posting that does not exist
    Then scout should refuse it
    And scout should say no such posting

  # --------------------------------------------------------------- afterwards

  # Months later, the question is "what did I actually send these people" — and
  # the answer has to be the words, not a reference to a file that has since
  # been tailored four more times.
  Scenario: Reading back what I approved
    Given I have approved a package for that posting
    When I read that package
    Then it should show the resume exactly as it was approved
    And it should show every answer exactly as it was approved

  # scout does not submit, so it cannot know for certain. What it can do is
  # record what was approved, and let the log say the rest.
  Scenario: Logging that it went
    Given I have approved a package for that posting
    When I log that posting as "applied"
    Then its status should be "applied"
    And that posting should still show the package I approved

  # ------------------------------------------------------- through the server

  # The reason this feature exists at all: the flow is a conversation, and the
  # package is what gets presented in it. If a model has to assemble this from
  # four tool calls and its own memory of them, it will get it wrong eventually
  # and confidently.
  Scenario: One call gets everything a session needs to present
    Given scout's MCP server running over stdio
    And I have assembled a package for that posting
    And I have added an answer to that package
    When I call the package tool for that posting
    Then the reply should include every item in the package
    And the reply should say which of them were checked
    And the reply should say what changed in the resume

  Scenario: Approving through the server
    Given scout's MCP server running over stdio
    And I have assembled a package for that posting
    When I call the approve tool for that posting
    Then the call should succeed
    And that package should be approved
