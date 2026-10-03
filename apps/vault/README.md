# vault

**https://vault.strange-lab.dev**, over MCP (Streamable HTTP), a bearer token
per client:

| Endpoint | What it is |
| --- | --- |
| `/servers/read/mcp` | the whole vault, read-only |
| `/servers/agents/mcp` | rooted at `Agents/`, read-write |

```sh
pnpm --filter vault run secret:github-token  # once, in a real terminal
pnpm --filter vault run secret:client-keys   # once: claude + paperclip tokens
pnpm --filter vault run diff
pnpm --filter vault run deploy   # refuses unpublished images; checks auth, both endpoints and the sync live
```

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

## Images

Built by CI from `Dockerfile.sync` and `Dockerfile.gateway`, and published to
GHCR only from `main` and only after the sync's specs pass:

- `ghcr.io/zstrangeway/vault-sync:<commit>` — this package, plus git.
- `ghcr.io/zstrangeway/vault-gateway:<commit>` — supergateway 4.1.0 in front of
  mcpvault 0.16.0, pinned rather than fetched by npx at every start.

Deploys pin the commit tag; `:main` only follows the branch.

supergateway 4.1.0 (the latest release) has no API-key options - its README
describes unreleased ones - so authentication is a Caddy container in front,
with the gateways listening only inside the pod.
