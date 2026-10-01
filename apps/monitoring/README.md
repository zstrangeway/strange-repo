# monitoring

Prometheus, Alertmanager and Grafana for the homelab cluster, from
[kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
91.8.2, trimmed. Infrastructure only: `values.yaml` is the whole of it.

**Grafana: http://grafana.home.arpa** (192.168.1.231) (user `admin`; password below).

## What it watches

The nodes (node-exporter), every Kubernetes object (kube-state-metrics), the
kubelets and the API server, with the chart's dashboards and alert rules for
all of them. Metrics are kept for 7 days on a 10Gi local-path volume —
pinned to one node, and gone if its disk goes.

Not scraped: etcd, the scheduler, the controller manager and kube-proxy.
Talos binds their metrics to localhost; exposing them is a Talos patch in the
homelab repo.

Apps add their own scrape targets with a `ServiceMonitor` or `PodMonitor`,
and their own alerts with a `PrometheusRule`, in their own namespace —
Prometheus picks them up from anywhere.

## Deploying

The cluster's kubeconfig is read from `~/Code/homelab/talos/_out/kubeconfig`
unless `KUBECONFIG` says otherwise.

```sh
pnpm --filter monitoring run secret:grafana-admin  # once
pnpm --filter monitoring run secret:slack-webhook  # once, in a real terminal
pnpm --filter monitoring run secret:healthchecks-ping  # once, in a real terminal
pnpm --filter monitoring run test     # values check, render, dry run
pnpm --filter monitoring run diff     # what deploy would change
pnpm --filter monitoring run deploy   # install, wait, check every target is up
```

`test` fails on any key in `values.yaml` the chart doesn't define — Helm
ignores those silently, so a typo or a key renamed by a chart upgrade would
otherwise do nothing. Until the chart's CRDs are installed, and without a
cluster, it checks rendering only and says so.

`deploy` fails if any target Prometheus scrapes is down: that is either a
real problem or a scrape that can't work on this cluster and should be
switched off in `values.yaml`.

## Alerts

Alertmanager posts to Slack through an incoming webhook (the Slack app
`homelab`; the webhook picks the channel). Firing alerts are red, resolved
ones green; a critical alert mutes the warning-level version of the same
thing.

**When the whole homelab is down**, nothing in it can say so. `Watchdog`
always fires, by design, and Alertmanager re-sends it every minute to a
[healthchecks.io](https://healthchecks.io) check (`homelab-watchdog`: period
5 minutes, grace 10). When the pings stop — power, network, Proxmox, the
cluster or Alertmanager itself — healthchecks.io posts to Slack on its own.
The ping URL is a credential too, stored by `secret:healthchecks-ping`.

The webhook URL is a credential: `secret:slack-webhook` reads it at a hidden
prompt and stores it in the cluster, and `deploy` refuses to run without it
or the ping URL. Replacing either is the same command.

To check the path end to end, post a test alert to Alertmanager's
`/api/v2/alerts` with an `endsAt` a couple of minutes out: a red message,
then a green one within about five minutes.

### Grafana's admin password

Generated into the cluster by `secret:grafana-admin` and never printed or
committed. To read it:

```sh
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d
```
