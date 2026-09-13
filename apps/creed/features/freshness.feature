Feature: Data that is never stale
  As someone checking a rule mid-game
  I want the answer to come from what Wahapedia says today
  So that I am not quoting a profile that changed in the last dataslate

  # This is the feature the whole app exists for, so it is the first one
  # specified. Everything else is lookup over a table; this is the part that
  # decides whether those tables are worth reading.
  #
  # The source is Wahapedia's official CSV export for 11th edition
  # (https://wahapedia.ru/wh40k11ed/the-rules/data-export/), not the HTML
  # site. Nineteen pipe-delimited files, ~8.3MB, republished within about
  # fifteen minutes of any site edit. No scraping, no HTML parsing, no
  # selector that breaks when the site is restyled.
  #
  # Freshness has an oracle: Last_update.csv is 39 bytes and holds one
  # timestamp covering the whole export. Checking it costs one request, so
  # creed can check often and download only when something actually moved.

  Background:
    Given a scratch creed directory

  # ------------------------------------------------------- the first sync

  Scenario: A first run has nothing and goes and gets it
    Given creed has never synced
    And the export is available
    When creed syncs
    Then every export table should be in the database
    And the database should record the export's update timestamp

  # Until the first sync lands there is no data, and an empty answer reads
  # exactly like "that unit does not exist". The difference matters: one is
  # a missing datasheet and the other is a server that has not started yet.
  Scenario: Asked something before the first sync ever ran
    Given creed has never synced
    When I look up any datasheet
    Then creed should say it has no data yet
    And creed should say how to sync

  # ------------------------------------------------------ staying current

  # One 39-byte request. This is what makes "never stale" affordable enough
  # to do on every startup and on an interval after that.
  Scenario: Checking costs one small request when nothing changed
    Given creed synced at the export's current timestamp
    When creed checks for updates
    Then creed should have fetched only the update marker
    And creed should not have downloaded any table

  Scenario: The export moved, so creed re-syncs
    Given creed synced at an older timestamp
    And the export has since been updated
    When creed checks for updates
    Then creed should download the tables again
    And the database should record the new timestamp

  # Conditional GET is honoured by the origin: every file carries an ETag and
  # a Last-Modified, and both return 304. A dataslate usually moves a handful
  # of files, so re-syncing should not re-download all 8.3MB.
  Scenario: A re-sync only pays for the files that changed
    Given creed synced at an older timestamp
    And the export has since been updated
    And only the points table actually differs
    When creed syncs
    Then the unchanged tables should have come back as not-modified
    And only the points table should have been downloaded in full

  # --------------------------------------------------- never a partial view

  # Eight megabytes over nineteen requests has plenty of room to fail halfway.
  # A database holding new stratagems against old datasheets is worse than
  # one holding yesterday's everything, because nothing about it looks wrong.
  Scenario: A sync that dies halfway leaves the old data intact
    Given creed has a complete sync from an older timestamp
    And the export has since been updated
    When the sync fails partway through
    Then creed should still answer from the older complete data
    And the recorded timestamp should still be the older one
    And creed should report that the sync failed

  Scenario: A table that arrives malformed is not written
    Given creed has a complete sync from an older timestamp
    And the export has since been updated
    And one table comes back with columns creed does not recognise
    When creed syncs
    Then creed should still answer from the older complete data
    And creed should name the table it could not read

  # ------------------------------------------------- when the network is out

  # Offline is the normal case at a table in a games club with bad signal.
  # Refusing to answer is the wrong call; answering without saying how old
  # the answer is, is the worse one.
  Scenario: Offline, with data already synced
    Given creed has a complete sync from an older timestamp
    And the export cannot be reached
    When I look up a datasheet
    Then creed should answer from what it has
    And the answer should say when the data was last synced

  Scenario: Offline, having never synced
    Given creed has never synced
    And the export cannot be reached
    When I look up a datasheet
    Then creed should say it has no data yet
    And creed should say it could not reach the export

  # -------------------------------------------------- saying how old it is

  # A model reading a tool result cannot see the sync log. If the answer does
  # not carry its own date, the model has no way to tell a human "this is
  # from before the September dataslate" — so every answer carries one.
  Scenario: Every answer carries the date of the data behind it
    Given creed has a complete sync
    When I look up a datasheet
    Then the answer should carry the export's update timestamp

  Scenario: Data old enough to be worth mentioning says so
    Given creed has a complete sync from well over a week ago
    And the export cannot be reached
    When I look up a datasheet
    Then the answer should warn that the data may be behind

  # ------------------------------------------------------------ attribution

  # Wahapedia asks for this in the export's own terms: "When publishing your
  # work, mentioning Wahapedia is highly recommended. For example, with the
  # inscription 'powered by Wahapedia'." It costs nothing and the data is the
  # entire product, so it is specified rather than left to whoever writes the
  # README.
  Scenario: Answers credit where the data came from
    Given creed has a complete sync
    When I look up a datasheet
    Then the answer should credit Wahapedia
    And the answer should link to the datasheet on Wahapedia
