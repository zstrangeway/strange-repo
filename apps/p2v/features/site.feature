Feature: Preserve the P2V website through the React migration
  The existing pages, accessible controls, and email inquiry flow keep working.

  Scenario Outline: Existing page addresses still load with the right content
    When I open "<path>"
    Then the main heading contains "<heading>"
    And the page has its title, description, and noindex metadata
    And all page images load
    And the page fits a mobile screen

    Examples:
      | path           | heading         |
      | /              | MORE THAN       |
      | /training.html | PUT IN          |
      | /teams.html    | YOUR TEAM.      |
      | /facility.html | WHERE THE       |
      | /about.html    | THE GAME        |
      | /schedule.html | MAKE TIME       |
      | /contact.html  | LET’S GET       |

  Scenario: Mobile navigation closes with Escape and restores focus
    Given I use a mobile screen
    When I open "/"
    And I open the menu
    And I press "Escape"
    Then the menu is closed and focused

  Scenario: Mobile navigation follows a link and marks the current page
    Given I use a mobile screen
    When I open "/"
    And I open the menu
    And I follow "Training" in the navigation
    Then the main heading contains "PUT IN"
    And "Training" is the current navigation page
    And the menu is closed

  Scenario: Resizing to desktop closes an open mobile menu
    Given I use a mobile screen
    When I open "/training.html"
    And I open the menu
    And I use a desktop screen
    And I use a mobile screen
    Then the menu is closed

  Scenario: Training tabs support click and keyboard selection
    When I open "/training.html"
    And I choose the "Strength & speed" training tab
    Then the training panel shows "Build the athlete behind the game."
    When I press "ArrowRight"
    Then the training panel shows "Grow beyond the court."
    When I press "ArrowRight"
    Then the training panel shows "Make the next rep matter."
    When I press "ArrowLeft"
    Then the training panel shows "Grow beyond the court."
    When I press "Home"
    Then the training panel shows "Make the next rep matter."
    When I press "End"
    Then the training panel shows "Grow beyond the court."

  Scenario Outline: Inquiry links preselect the intended interest
    When I open "/contact.html?interest=<query>"
    Then the inquiry interest is "<interest>"

    Examples:
      | query          | interest       |
      | Training       | Training       |
      | Camps          | Camps          |
      | 14U%20Team      | 14U Team       |
      | 16U%20Team      | 16U Team       |
      | Tryouts        | Tryouts        |
      | Schedule       | Schedule       |
      | Something%20else | Something else |
      | Unknown        | Training       |

  Scenario: Reviewing a message prepares an encoded email and lets me edit again
    When I open "/contact.html?interest=Camps"
    And I complete the inquiry form
    And I review the message
    Then I see my message and a matching email link
    When I edit my message
    Then the email preview is hidden
    When I review the message
    Then I see my edited message

  Scenario: Required fields prevent an incomplete inquiry
    When I open "/contact.html"
    And I review the message
    Then the email preview is hidden
    And the inquiry form is invalid

  Scenario: Optional athlete details can be omitted
    When I open "/contact.html"
    And I complete the inquiry form without athlete details
    And I review the message
    Then the email preview omits athlete details

  Scenario: Copying the reviewed inquiry reports success
    Given clipboard writes succeed
    When I open "/contact.html"
    And I complete the inquiry form
    And I review the message
    And I copy the message
    Then the copy status is "Message copied."
    And the clipboard contains the reviewed message

  Scenario: Clipboard failures offer a manual alternative
    Given clipboard writes fail
    When I open "/contact.html"
    And I complete the inquiry form
    And I review the message
    And I copy the message
    Then the copy status is "Select the message above to copy it manually."

  Scenario: Frequently asked questions remain expandable
    When I open "/contact.html"
    And I expand "Does this form register my athlete?"
    Then I can read "No. It prepares an email inquiry."
