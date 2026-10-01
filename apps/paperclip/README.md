# paperclip

[Paperclip](https://paperclip.ing) 2026.916.1, orchestration for a team of AI
agents, at **http://paperclip.home.arpa** (192.168.1.232). Infrastructure
only: the server image and Postgres 17.11, configured here.

Agents run inside the server pod through the CLIs the image ships: Claude
Code (`claude_local`, reads `ANTHROPIC_API_KEY`) and OpenCode
(`opencode_local`, here with `OPENROUTER_API_KEY`). Budget: $50/month, set in
Paperclip itself.

## Deploying

```sh
pnpm --filter paperclip run secret:internal    # once: db password + 3 app secrets
pnpm --filter paperclip run secret:model-keys  # in a real terminal; hidden prompts
pnpm --filter paperclip run test
pnpm --filter paperclip run diff
pnpm --filter paperclip run deploy             # apply, wait, check /api/health
```

`secret:internal` never rotates what exists: a new database password or
secrets master key would lock out the existing data.

## First admin

A fresh install is `bootstrap_pending`: open the URL, create an account, and
choose **Claim this instance**. The first claim wins — fine on the LAN, but
don't leave a fresh install unclaimed.

## Things that bite

- **Private mode 403s any Host it doesn't know** — including the kubelet's
  probes, which arrive by pod IP. Browser-facing names are in
  `PAPERCLIP_ALLOWED_HOSTNAMES`; the probes send `Host: localhost`, which is
  always allowed. A new name for it needs adding there.
- **Storage is local-path**: Postgres (5Gi) and `/paperclip` (10Gi, agent
  workspaces) are each pinned to one node and gone with its disk. Paperclip's
  own hourly DB backups land on the same volume, so they don't cover that.
