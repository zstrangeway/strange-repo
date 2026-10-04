# homeassistant

[Home Assistant](https://www.home-assistant.io) 2026.9.4, home automation, at
**https://home.strange-lab.dev** (through apps/proxy). Infrastructure only:
the official image, configured here.

## Deploying

```sh
pnpm --filter homeassistant test
pnpm --filter homeassistant diff
pnpm --filter homeassistant deploy  # apply, wait, check the URL answers
```

Then open the URL and complete onboarding — the first account created is the
owner, so don't leave a fresh install unclaimed.

## Things that bite

- **`configuration.yaml` is in git** ([config/configuration.yaml](config/configuration.yaml)),
  mounted over the file on the volume. Edit it here and redeploy; the pod
  rolls. Everything Home Assistant writes itself — users, integrations set up
  in the UI, the recorder database — lives on the volume beside it.
- **It runs as root.** The image's s6-overlay init refuses to start as any
  other user, so there is no `runAsNonRoot` lockdown like apps/homepage's.
- **`trusted_proxies` is the pod network** (`10.244.0.0/16`). Behind Traefik,
  HA refuses a request whose `X-Forwarded-For` arrives from an address it
  doesn't trust — if the Ingress answers 400, that range doesn't match the
  cluster's pod CIDR, and the fix is one line in config/configuration.yaml.
- **No host networking, so no auto-discovery.** mDNS/SSDP see nothing;
  integrations for devices reachable by IP still work. Discovery needs
  `hostNetwork: true` and `dnsPolicy: ClusterFirstWithHostNet` on the pod.
- **Storage is local-path**: `/config` (2Gi) is pinned to one node and gone
  with its disk. Home Assistant's own backup integration (to cloud storage)
  is the way off that.
