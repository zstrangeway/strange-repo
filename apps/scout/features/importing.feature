Feature: Getting a real resume in
  As somebody whose resume is a PDF like everybody else's
  I want scout to turn it into the file it reads
  So that the first five minutes are not spent reformatting by hand

  # scout reads `resumes/master.md`, and nobody has a markdown resume. Somebody
  # converting four pages by hand before they can try the tool will not try it.
  #
  # **The model reads the structure and a deterministic check proves it changed
  # nothing.** Recognising which line is an employer is what a model is
  # genuinely better at than a rule: formats vary without limit, and a parser
  # chasing them gets more fragile with every one it learns. The first version
  # of this was regular expressions, and teaching it two employers it had
  # missed silently lost it seven it had been finding.
  #
  # What a model cannot be trusted with is the content. The master resume is
  # the document every other check is made against, so an importer that
  # dropped a job or reworded a bullet would poison the one source of truth
  # scout has — and every check downstream would agree with it, because it
  # would be checking against the damage.
  #
  # So the verifier requires word conservation **in both directions**: every
  # word of the original must survive, and no word may appear that was not
  # there before. That is tighter than tailoring's check — there the model is
  # meant to rewrite, so only new names can be caught; here nothing may change
  # at all, so everything can be.

  Background:
    Given a scratch scout directory

  Scenario: Importing a resume
    Given a resume file with two employers and a skills section
    When I import it
    Then a master resume should be written
    And it should have both employers as headings
    And scout should say how many employers it found

  Scenario: The words are guaranteed and the structure is not
    Given a resume file with two employers and a skills section
    When I import it
    Then scout should say every word survived and none were added
    And scout should tell me to read the result

  # The refusals below are the feature. Without them this is just asking a
  # model to rewrite the one document scout trusts.
  Scenario: A conversion that drops something
    Given a resume file with two employers and a skills section
    And the model will return it with a job missing
    When I import it
    Then scout should refuse it
    And scout should say what it dropped
    And no master resume should have been written

  Scenario: A conversion that invents something
    Given a resume file with two employers and a skills section
    And the model will return it with a skill added
    When I import it
    Then scout should refuse it
    And scout should say what it added
    And no master resume should have been written

  # A running header carrying somebody's name is on every page of the PDF and
  # is not content. Insisting the output keep all six copies would refuse
  # every real resume; dropping all six would make the name at the top read as
  # something the importer invented.
  Scenario: A page header repeated on every page
    Given a resume file whose name is repeated as a page header
    When I import it
    Then a master resume should be written
    And the master resume should still have the name in it

  Scenario: Not overwriting a master resume by accident
    Given a resume file with two employers and a skills section
    And I have already imported it
    When I import it again
    Then scout should refuse it
    And scout should say the master resume is already there

  Scenario: Overwriting on purpose
    Given a resume file with two employers and a skills section
    And I have already imported it
    When I import it again, replacing what is there
    Then a master resume should be written

  Scenario: A file that is not there
    When I import a file that does not exist
    Then scout should refuse it
    And scout should say where it looked
