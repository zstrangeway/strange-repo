# vault

Zac's Obsidian vault (the private `zstrangeway/vault` repo), served to the
homelab's agents over MCP, with their writes kept in git. Agents read the
whole vault and write memory only into `Agents/` — see the vault's own
`Agents/README.md` for the rules they follow.

## vault-sync

The one piece of code here: beside the MCP server, about once a minute, it

1. commits agent changes under `Agents/` — and nothing else — as
   "homelab agents", naming every file in the message;
2. pulls Zac's edits from his devices (rebasing, so history stays linear);
3. pushes, pulling and retrying if a device pushed first.

A real conflict stops it with both versions intact and nothing pushed: it
exits non-zero, the pod restarts, and a crash-looping pod is already
something monitoring alerts on. Resolve it by hand, and it carries on.

Specified in `features/vault-sync.feature`; the specs run real git
repositories (a stand-in for GitHub, Zac's laptop, and the server's copy) so
pulls, pushes, races and conflicts happen for real.

```sh
pnpm --filter vault run test    # lint, specs and unit tests, 100% coverage
```
