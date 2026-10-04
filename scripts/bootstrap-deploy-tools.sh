#!/usr/bin/env bash
set -euo pipefail

# Bootstrap pinned, sha256-verified deploy tooling into a workspace-local bin
# directory. Idempotent: re-running skips tools that are already present and
# verified. The default bin dir is the repo root's .bin/; pass a path as the
# first argument or set DEPLOY_TOOLS_BIN to override.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="${1:-${DEPLOY_TOOLS_BIN:-$REPO_ROOT/.bin}}"
mkdir -p "$BIN_DIR"

KUBECTL_VERSION="v1.37.1"
KUBECTL_SHA256="65691ff77eb6fa44c908b77a1082c9f092c3b9733b5cefabec0d1104890e21a8"
KUBECTL_URL="https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"

TASK_VERSION="v3.52.0"
TASK_SHA256="02c679ffae53dca791804847d78b31731615894e292948397c971c87ac9e95bd"
TASK_URL="https://github.com/go-task/task/releases/download/${TASK_VERSION}/task_linux_amd64.tar.gz"

YQ_VERSION="v4.44.6"
YQ_SHA256="0c2b24e645b57d8e7c0566d18643a6d4f5580feeea3878127354a46f2a1e4598"
YQ_URL="https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64"

sha_matches() {
  local file=$1 expected=$2
  [ -f "$file" ] || return 1
  printf '%s  %s\n' "$expected" "$file" | sha256sum -c - >/dev/null 2>&1
}

download_binary() {
  local name=$1 url=$2 dest=$3 expected=$4
  local tmp
  tmp=$(mktemp)
  trap 'rm -f "$tmp"' EXIT
  echo "Downloading $name ($url) ..."
  curl -fsSL "$url" -o "$tmp"
  printf '%s  %s\n' "$expected" "$tmp" | sha256sum -c -
  mv "$tmp" "$dest"
  chmod +x "$dest"
  trap - EXIT
}

if sha_matches "$BIN_DIR/kubectl" "$KUBECTL_SHA256"; then
  echo "kubectl already present and verified"
else
  download_binary kubectl "$KUBECTL_URL" "$BIN_DIR/kubectl" "$KUBECTL_SHA256"
fi

if [ -x "$BIN_DIR/task" ] && "$BIN_DIR/task" --version 2>/dev/null | grep -q "${TASK_VERSION#v}"; then
  echo "task $TASK_VERSION already present"
else
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' EXIT
  echo "Downloading task $TASK_VERSION ..."
  curl -fsSL "$TASK_URL" -o "$tmpdir/task.tar.gz"
  printf '%s  %s\n' "$TASK_SHA256" "$tmpdir/task.tar.gz" | sha256sum -c -
  tar -xzf "$tmpdir/task.tar.gz" -C "$BIN_DIR" task
  chmod +x "$BIN_DIR/task"
  trap - EXIT
fi

if sha_matches "$BIN_DIR/yq" "$YQ_SHA256"; then
  echo "yq already present and verified"
else
  download_binary yq "$YQ_URL" "$BIN_DIR/yq" "$YQ_SHA256"
fi

echo ""
echo "Deploy tools ready in $BIN_DIR:"
"$BIN_DIR/kubectl" version --client
"$BIN_DIR/task" --version
"$BIN_DIR/yq" --version
