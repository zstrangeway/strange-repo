Feature: P2V Academy website app
  The existing P2V Academy refresh runs as apps/p2v-academy in strange-repo.
  Preserve its approved orange, charcoal, and silver design and coherent copy.
  Use the existing workspace Next.js stack and shared UI components.
  App commands delegate to Taskfile.yml and join the workspace test gate.

  Scenario Outline: Browse the academy pages
    When a visitor opens the "<page>" page directly
    Then the page loads with its P2V content and navigation
    And its images, fonts, and styles load successfully
    And the navigation identifies the current page
    Examples:
      | page     |
      | Home     |
      | Training |
      | Teams    |
      | About    |
      | Schedule |
      | Contact  |
      | Facility |

  Scenario: Preserve existing links
    When a visitor opens an existing .html page URL
    Then the corresponding academy page is accessible

  Scenario: View the approved design on different screens
    When a visitor views the site on desktop or mobile
    Then the layout fits the viewport without horizontal overflow
    And the design uses the approved athletic branding
    And decorative arrow graphics are absent
    And the earlier phone photos of the branding are absent

  Scenario: Tour the facility
    When a visitor opens the Facility page
    Then the court photo shows the version with all people removed
    And the strength area photo is displayed
    And the unedited court photo is not shipped as an app asset

  Scenario: Use mobile navigation
    Given a visitor is using a mobile viewport
    When they open the navigation menu
    Then the page links are visible and the menu reports expanded
    When they press Escape
    Then the menu closes and focus returns to its button
    When they open the menu and follow a link
    Then the menu closes
    When they resize an open menu to desktop width
    Then the mobile menu state resets

  Scenario: Explore training focus areas
    Given a visitor is on the Training page
    When they select Skills, Athletic Development, or Mindset
    Then the selected tab and associated content update together
    And Left, Right, Home, and End keys support tab navigation

  Scenario: Prepare an inquiry
    Given a visitor fills the required contact fields
    When they prepare their inquiry
    Then a readable message preview appears
    And an email link addresses p2vacademy@gmail.com with the inquiry
    And no message is sent automatically
    And athlete name and age remain optional
    And special characters remain intact in the message
    When they edit a field
    Then the stale preview is hidden

  Scenario: Prefill an inquiry interest
    When a visitor follows a contact link with a supported interest
    Then that interest is selected in the form
    When a visitor follows a contact link with an unsupported interest
    Then the form retains its default interest

  Scenario: Copy an inquiry
    Given a visitor has prepared an inquiry
    When they copy the message
    Then successful clipboard access reports that the message was copied
    And denied clipboard access provides manual copying instructions

  Scenario: Retain preview status
    When a visitor opens any academy page
    Then the design-preview notice remains visible
    And search-engine indexing remains disabled
