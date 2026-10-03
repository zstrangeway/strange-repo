# omarchy-heart

A heart in the [Omarchy](https://omarchy.org) bar, next to Wi-Fi. Clicking it
drops down a panel, styled like the built-in network and power panels, listing
people's birthdays and anniversaries with a countdown to each:

```
Alex
  🎂  April 12, 1990 (36)       191 days
  ♥   June 20, 2015 (11)        260 days
Sam
  🎂  November 3, 2012 (13)      31 days
```

- Colors follow the active Omarchy theme.
- The bar heart turns the accent color when a date is within `soonDays`, and
  pulses on the day itself; that day's row is highlighted.
- `heart-reminders.timer` checks hourly and sends a desktop notification once
  when a date comes within `soonDays`, and again on the day - between 9am and
  10pm only.

It is configuration plus a little code for software we didn't write, kept here
so it survives a reinstall. Its code has no specs or tests.

## Install

```sh
task omarchy-heart:install
omarchy plugin enable zstrangeway.heart
omarchy bar move zstrangeway.heart --section right --index 4   # optional: beside Wi-Fi
```

## Configure

Names, dates and the panel title live only in the widget's entry in
`~/.config/omarchy/shell.json`, never in this repository. Copy the shape from
[`config.example.json`](config.example.json) into that entry:

| Key | Meaning |
| --- | --- |
| `title` | Heading under the heart, and the notifications' app name |
| `people` | `name`, plus `birthday` and/or `anniversary` as `YYYY-MM-DD`, or `MM-DD` to leave out the year (and the age) |
| `soonDays` | How many days ahead the bar heart lights up and the first reminder goes out. Default 7 |

The panel picks up edits to `shell.json` as soon as they're saved. The number
in brackets is the age, or the years together, as of today.
