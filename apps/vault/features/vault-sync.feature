Feature: Keep the agents' memory in the vault repository
  The vault is a git repository that Zac edits from his devices through
  Obsidian. In the homelab, agents write memory into its Agents/ folder
  through an MCP server. A sync process, running beside that server, makes
  sure every agent write ends up in the repository - and that it never
  touches anything else, never loses Zac's edits, and never fails quietly.

  Background:
    Given a vault repository shared with Zac's devices
    And a working copy of it beside the MCP server

  Scenario: An agent's new note is committed and pushed
    Given an agent has written "Agents/Claude/Homelab DNS.md"
    When the sync runs
    Then the repository has a commit adding "Agents/Claude/Homelab DNS.md"
    And the commit is authored by "homelab agents"
    And the commit message names the files it changed

  Scenario: Nothing changed, so nothing is committed
    Given no file has changed since the last sync
    When the sync runs
    Then no commit is made
    And the sync reports that there was nothing to commit

  Scenario: Zac's edits from his devices arrive before agent changes are committed
    Given Zac has pushed a change to "Inbox/Idea.md" from his laptop
    And an agent has written "Agents/Shared/Index.md"
    When the sync runs
    Then the working copy has Zac's change to "Inbox/Idea.md"
    And the repository has both changes

  Scenario: Only the Agents folder is ever committed
    Given "Inbox/Idea.md" has been changed in the working copy
    And an agent has written "Agents/Claude/Index.md"
    When the sync runs
    Then the commit contains only "Agents/Claude/Index.md"
    And the sync reports that it left "Inbox/Idea.md" uncommitted

  Scenario: A push that loses a race is retried after pulling
    Given an agent has written "Agents/Claude/Index.md"
    And Zac pushes a change to "Inbox/Idea.md" just before the sync pushes
    When the sync runs
    Then the agent's change reaches the repository
    And Zac's change is not lost

  Scenario: A conflicting edit stops the sync rather than overwriting anything
    Given Zac and an agent have both changed "Agents/Shared/Index.md" in different ways
    When the sync runs
    Then nothing is pushed
    And neither version is overwritten
    And the sync reports the conflict and exits with a failure
