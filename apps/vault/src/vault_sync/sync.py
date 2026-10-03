"""Keep the agents' memory in the vault repository.

Agents write into Agents/ through the MCP server; this commits those writes
and nothing else, brings in Zac's edits from his devices first, and pushes.
It never resolves a conflict on anyone's behalf: a real conflict stops it,
loudly, with both versions intact.
"""

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

AGENTS = "Agents/"
AUTHOR_NAME = "homelab agents"
AUTHOR_EMAIL = "agents@homelab.invalid"


class SyncError(Exception):
    """A sync that must not continue - the message says why, for a human."""


@dataclass
class Report:
    committed: list[str] = field(default_factory=list)
    left_uncommitted: list[str] = field(default_factory=list)
    pushed: bool = False

    def lines(self) -> list[str]:
        out = []
        if self.committed:
            out.append(f"committed {len(self.committed)} file(s): {', '.join(self.committed)}")
        else:
            out.append("nothing to commit")
        if self.left_uncommitted:
            out.append(f"left uncommitted (outside {AGENTS}): {', '.join(self.left_uncommitted)}")
        out.append("pushed" if self.pushed else "nothing to push")
        return out


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    # check=False: the return code is examined below, to raise a readable error.
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise SyncError(f"git {' '.join(args)} failed: {(result.stderr or result.stdout).strip()}")
    return result


def changed_paths(repo: Path) -> list[str]:
    # -z: paths exactly as git has them, spaces and all; -uall: each new file
    # inside a new folder, not just the folder.
    out = git(repo, "status", "--porcelain", "-z", "-uall").stdout
    return sorted({entry[3:] for entry in out.split("\0") if entry})


def commit_agent_changes(repo: Path, report: Report) -> None:
    paths = changed_paths(repo)
    report.left_uncommitted = [p for p in paths if not p.startswith(AGENTS)]
    agent_paths = [p for p in paths if p.startswith(AGENTS)]
    if not agent_paths:
        return
    git(repo, "add", "--all", "--", AGENTS)
    message = "agents: update memory\n\n" + "\n".join(f"- {p}" for p in agent_paths)
    git(
        repo,
        "-c",
        f"user.name={AUTHOR_NAME}",
        "-c",
        f"user.email={AUTHOR_EMAIL}",
        "commit",
        "--quiet",
        "--message",
        message,
    )
    report.committed = agent_paths


def pull(repo: Path, remote: str, branch: str) -> None:
    # --autostash: changes left outside Agents/ ride along untouched.
    result = git(repo, "pull", "--rebase", "--autostash", remote, branch, check=False)
    if result.returncode == 0:
        return
    conflicted = git(repo, "diff", "--name-only", "--diff-filter=U").stdout.split()
    git(repo, "rebase", "--abort", check=False)
    if conflicted:
        raise SyncError(f"conflict in {', '.join(conflicted)}: both versions kept, nothing pushed - resolve it by hand")
    raise SyncError(f"pull failed: {(result.stderr or result.stdout).strip()}")


def ahead(repo: Path, remote: str, branch: str) -> bool:
    return git(repo, "rev-list", "--count", f"{remote}/{branch}..HEAD").stdout.strip() != "0"


def sync(repo: Path, remote: str = "origin", branch: str = "main", attempts: int = 3) -> Report:
    report = Report()
    commit_agent_changes(repo, report)
    for _ in range(attempts):
        pull(repo, remote, branch)
        if not ahead(repo, remote, branch):
            return report
        if git(repo, "push", "--quiet", remote, f"HEAD:{branch}", check=False).returncode == 0:
            report.pushed = True
            return report
        # Someone pushed in between: pull their change and go again.
    raise SyncError(f"push still rejected after {attempts} attempts")


def run(repo: Path, interval: float, once: bool, sleep=time.sleep) -> int:
    while True:
        try:
            for line in sync(repo).lines():
                print(f"vault-sync: {line}", flush=True)
        except SyncError as e:
            # Exiting is the alarm: the pod restarts until a human looks, and
            # a crash-looping pod is already something monitoring reports.
            print(f"vault-sync: FAILED - {e}", file=sys.stderr, flush=True)
            return 1
        if once:
            return 0
        sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", type=Path, help="the vault's working copy")
    parser.add_argument("--interval", type=float, default=60, help="seconds between syncs")
    parser.add_argument("--once", action="store_true", help="sync once and exit")
    args = parser.parse_args(argv)
    return run(args.repo, args.interval, args.once)
