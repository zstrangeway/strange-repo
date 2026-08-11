Feature: Profile
  As a signed-in user
  I want a page showing my details
  So that I can correct my name

  Background:
    Given I have signed in at google as "ada@example.com" named "Ada"

  Scenario: Viewing my profile
    When I open the profile page
    Then the page shows my email "ada@example.com"
    And the page shows my display name "Ada"

  Scenario: A signed-out visitor cannot open a profile
    Given I am signed out
    When I open the profile page
    Then I should be on the sign in page

  Scenario: Changing my display name changes what gary calls me
    When I open the profile page
    And I change my display name to "Ada Lovelace"
    Then the page shows a confirmation
    When I open the home page
    Then I should be signed in as "Ada Lovelace"

  Scenario: A blank display name is refused
    When I open the profile page
    And I change my display name to "   "
    Then the page shows an error about the display name
