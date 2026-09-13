# creed

Warhammer 40,000 rules and stats, as an MCP server and a command line tool.
Named for Ursarkar E. Creed, Lord Castellan of Cadia.

Data comes from [Wahapedia's data export][export] for 11th edition — the
sanctioned CSV bulk download, not a scrape of the site. Twenty-one
pipe-delimited files, about 8.4MB, republished within roughly fifteen minutes
of any edit to the site.

Powered by [Wahapedia][waha]. Please consider supporting the project there.

[export]: https://wahapedia.ru/wh40k11ed/the-rules/data-export/
[waha]: https://wahapedia.ru

## Using it from Claude Code

```json
{
  "mcpServers": {
    "creed": {
      "command": "uv",
      "args": ["run", "--directory", "apps/creed", "creed-mcp"]
    }
  }
}
```

The server syncs on startup and then answers from the local database. Set
`CREED_SYNC_ON_START=0` to skip that and use whatever was last synced.

## On the command line

```
creed sync                       # pull the current export
creed status                     # how fresh the data is
creed search contemptor          # find datasheets
creed show "Custodian Guard"     # one datasheet, whole
creed stratagems --phase Shooting --turn "Your turn" --max-cp 1
creed detachments --faction "Adeptus Custodes"
creed attack "Custodian Guard" "Nobz" --weapon "Guardian spear" --models 4
creed list new my-army "Adeptus Custodes" --points 2000
creed list check 1
```

`creed list check` reports what it checked and names the core rules it cannot
check. It never says a list is legal.
