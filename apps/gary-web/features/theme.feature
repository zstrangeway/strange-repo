Feature: Theme
  As someone using gary
  I want to choose light or dark instead of taking whatever the machine says
  So that I can read it the way I prefer, including on a machine I do not control

  # The choice is kept in localStorage, so it belongs to the browser rather
  # than the account: signing in elsewhere does not carry it across, and
  # clearing site data forgets it. That is the trade for not involving the
  # server in what is only ever a display preference.

  Background:
    Given I am signed in as "Ada"

  Scenario: With no choice made, the system decides
    Given my system is set to dark
    When I open the home page
    Then the page is dark

  Scenario: With no choice made, a light system decides too
    Given my system is set to light
    When I open the home page
    Then the page is light

  Scenario: Choosing dark overrides a light system
    Given my system is set to light
    When I open the home page
    And I choose the "Dark" theme
    Then the page is dark

  Scenario: Choosing light overrides a dark system
    Given my system is set to dark
    When I open the home page
    And I choose the "Light" theme
    Then the page is light

  Scenario: My choice outlives the page it was made on
    Given my system is set to light
    When I open the home page
    And I choose the "Dark" theme
    And I open the profile page
    Then the page is dark

  Scenario: My choice survives a reload
    Given my system is set to light
    When I open the home page
    And I choose the "Dark" theme
    And I reload the page
    Then the page is dark

  Scenario: Handing the decision back to the system
    Given my system is set to dark
    When I open the home page
    And I choose the "Light" theme
    And I choose the "System" theme
    Then the page is dark
