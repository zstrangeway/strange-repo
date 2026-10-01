# dns

Local hostnames for the homelab, under `home.arpa`, kept in the UDM's own DNS
by [external-dns](https://github.com/kubernetes-sigs/external-dns) v0.23.0
and the [UniFi webhook](https://github.com/home-operations/external-dns-unifi-webhook)
0.10.12. Infrastructure only.

Devices already ask the UDM for DNS, so nothing on the network changes: the
UDM just knows more names. They resolve on the LAN only, not over Tailscale.

| Name | Points at | Declared in |
| --- | --- | --- |
| `proxmox.home.arpa` | 192.168.1.200 | `static.yaml` |
| `talos-cp1/-w1/-w2.home.arpa` | .201–.203 | `static.yaml` |
| `homepage.home.arpa` | 192.168.1.230 | `apps/homepage/service.yaml` |
| `grafana.home.arpa` | 192.168.1.231 | `apps/monitoring/values.yaml` |

## Adding a name

For an app: annotate its `LoadBalancer` Service with
`external-dns.kubernetes.io/hostname: <name>.home.arpa`. Not
`external-dns.alpha.kubernetes.io/` — external-dns ignores that prefix since
v0.22, silently, and `test` fails on it. For anything else, add it to
`static.yaml`.

external-dns only writes inside `home.arpa`, and only changes or deletes
records it created (it marks its own with TXT records), so anything added by
hand in UniFi is left alone. If the cluster is down, the records stay in the
UDM; they just stop updating.

## Deploying

```sh
pnpm --filter dns run secret:unifi-api-key  # once, in a real terminal
pnpm --filter dns run test     # values check, prefix check, render, dry run
pnpm --filter dns run diff     # what deploy would change, and every declared name
pnpm --filter dns run deploy   # install, then ask the UDM for every name
```

`deploy` gathers every declared name — `static.yaml` plus every annotated
Service — and fails unless the UDM itself answers each with the right IP
(`tools/dns_lookup.py`, which skips every local cache).

### The UniFi API key

From the UDM's **Integrations** (its own tab in the Network app's left nav).
`secret:unifi-api-key` reads it at a hidden prompt, checks the UDM accepts it
with one read-only call, and stores it in the cluster. Least privilege: create
it as a dedicated admin, then drop that admin to Site Admin.
