# homepage

[Homepage](https://gethomepage.dev) v2.4.0, the homelab's dashboard, at
**http://homepage.home.arpa** (192.168.1.230). Infrastructure only: these are the official
Kubernetes manifests, adapted, and the dashboard's config — no code of ours.

## What it shows

- **UniFi** — uptime, WAN, and wired and Wi-Fi clients. It uses apps/dns's
  UniFi API key, copied in by `secret:unifi-api-key`: more access than a
  read-only widget needs, chosen over maintaining a separate UniFi admin.
- **Proxmox** — the host's status, VMs and resources, through a read-only API
  token.
- **The cluster** — CPU and memory for the cluster and each node. Needs
  metrics-server (installed by the homelab repo's `task platform:deploy`):
  without it the widget errors on every refresh, even with CPU and memory
  off.

Edit the dashboard in `config/`. Each file there is mounted as Homepage's file
of the same name; a change gives the ConfigMap a new name, which rolls the pod.

## Deploying

The cluster's kubeconfig is read from `~/Code/homelab/talos/_out/kubeconfig`
unless `KUBECONFIG` says otherwise.

```sh
pnpm --filter homepage run test     # render, parse, and server-side dry run
pnpm --filter homepage run diff     # what deploy would change
pnpm --filter homepage run deploy   # apply, wait, and check it answers
```

`run` is needed: `pnpm deploy` is a built-in pnpm command (it copies a
package into a folder) and wins over the script of the same name.

`test` asks the cluster's API to validate every object when a cluster is
reachable, and says it skipped that when one isn't — so in CI it checks
rendering and YAML only.

### The Proxmox token

Not in this repo. `deploy` refuses to run until it exists. From the homelab
repo:

```sh
task secret:proxmox-token APP=homepage
```

It lands in the `homepage/proxmox-token` Secret, and the Deployment passes it
to Homepage as `HOMEPAGE_VAR_PROXMOX_*`, which `config/services.yaml`
references.

## Changing its address

`192.168.1.230` and `homepage.home.arpa` are set in `service.yaml` (the
MetalLB and external-dns annotations), and both must also be in
`HOMEPAGE_ALLOWED_HOSTS` in `deployment.yaml`. Homepage answers any host not
listed there with an error page.
