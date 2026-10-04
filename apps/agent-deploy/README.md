# agent-deploy

RBAC kit and tooling bootstrap so the Paperclip agent runner can deploy
plain-kustomize infrastructure apps to the homelab cluster.

The runner pod authenticates as `system:serviceaccount:paperclip:default`.
This app grants that identity the smallest set of rights needed to apply
manifests in [`apps/homeassistant`](../homeassistant) and
[`apps/homepage`](../homepage).

## One-time user grant

Apply this app once from a `strange-repo` checkout on a machine with `kubectl`
and the cluster kubeconfig:

```sh
kubectl apply -k apps/agent-deploy
```

This is intentionally a human action. Agents never grant themselves access.

## What gets granted

- ClusterRole `paperclip-agent-deploy-bootstrap`: `namespaces` get/list/create.
  This is needed because each app ships its own `namespace.yaml`. The tradeoff:
  the agent can create namespaces, but it cannot modify or delete existing
  namespaces.
- Role `paperclip-agent-deploy` in namespaces `homeassistant` and `homepage`:
  core `configmaps`, `persistentvolumeclaims`, `services`, `serviceaccounts`
  (get/list/watch/create/update/patch); `pods` (get/list/watch only); `apps`
  `deployments` and `statefulsets` (get/list/watch/create/update/patch);
  `networking.k8s.io` `ingresses` (get/list/watch/create/update/patch).
- No `secrets`, no `delete`, no cluster-scoped changes beyond namespace
  creation.

## Verify access

After the grant, an agent can check:

```sh
kubectl auth can-i create deployments -n homeassistant --as=system:serviceaccount:paperclip:default
```

Expected: `yes`.

## Deploy flow

For an app the grant covers (currently `homeassistant` or `homepage`), from a
checkout of `main` at the merged SHA:

```sh
kubectl apply -k apps/<app>
kubectl rollout status -n <ns> deploy/<app>
curl -fsSL https://<ingress-host>/
```

Example for `homeassistant`:

```sh
kubectl apply -k apps/homeassistant
kubectl rollout status -n homeassistant deploy/homeassistant
curl -fsSL https://home.strange-lab.dev/
```

## Tooling bootstrap

The runner workspace may not have `kubectl`, `task`, or `yq`.
[`scripts/bootstrap-deploy-tools.sh`](../../scripts/bootstrap-deploy-tools.sh)
downloads pinned, sha256-verified binaries into a workspace-local `bin/`
directory:

```sh
scripts/bootstrap-deploy-tools.sh
# or with a custom bin dir:
scripts/bootstrap-deploy-tools.sh /path/to/bin
```

## What stays user-only

- [`apps/paperclip`](../paperclip) — the runner's own namespace; agents do not
  modify their own plane.
- Helm-based apps: `apps/proxy`, `apps/dns`, `apps/monitoring`, `apps/vault`.
- Anything needing `delete`, `prune`, force-replace, or `Secret` writes.
- The sops/age key, kubeconfig, Talos/Proxmox/ssh access, and cluster-level
  infrastructure.

## Testing

```sh
pnpm --filter agent-deploy test
```

If `kubectl` is not available, the test reports that and skips rendering rather
than passing silently.
