# proxy

[Traefik](https://traefik.io) v3.7.13 (chart 41.6.1): HTTPS for the
homelab's apps, at 192.168.1.233. Infrastructure only.

One Let's Encrypt **wildcard**, `*.strange-lab.dev`, proved through
Cloudflare DNS and renewed by Traefik. A wildcard rather than one certificate
per app, so app names stay out of the public certificate-transparency logs.
Port 80 redirects to 443.

**Private by design.** The names exist only in the UDM (apps/dns) and, away
from home, through Tailscale split DNS (`strange-lab.dev` → 192.168.1.1).
Nothing about the homelab is in public DNS; proving the domain only needs a
temporary TXT record. Off the LAN, only Tailscale devices reach any of it.

## Adding an app

Give it an Ingress with `ingressClassName: traefik` and a
`<name>.strange-lab.dev` host. The wildcard covers it; apps/dns points the
name at .233 from the Ingress's status.

## Deploying

```sh
pnpm --filter proxy run secret:cloudflare-token  # once, in a real terminal
pnpm --filter proxy run test     # values check, render, dry run
pnpm --filter proxy run diff
pnpm --filter proxy run deploy   # install, then show the certificate actually served
```

The token is a Cloudflare API token, "Edit zone DNS" on strange-lab.dev only
(plus Zone:Read); the task checks it's active and sees the zone before storing.

`https://probe.strange-lab.dev/ping` is Traefik's own route. It's there
because certificates are requested for routes: without one, nothing is issued.

## Things that bite

- **Staging first** for anything that changes how certificates are obtained
  (`letsencrypt-staging` is kept configured): production's rate limits can
  lock issuance out for days.
- **Switching resolvers isn't enough.** A certificate still in the other
  resolver's store counts as covering the names, so Traefik never asks the
  new one. Empty the old store (`: > /data/acme-staging.json` in the pod) and
  restart.
- **`helm template` offline** needs `--api-versions monitoring.coreos.com/v1`,
  or the chart refuses to render its ServiceMonitor.
