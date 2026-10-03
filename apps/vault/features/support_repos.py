"""Real git repositories for a scenario: a stand-in for GitHub, Zac's laptop,
and the working copy beside the MCP server. Shared with the unit tests."""

import subprocess
from pathlib import Path

SEED = {
    "README.md": "# Vault\n",
    "Agents/Shared/Index.md": "# Shared memory\n",
    "Inbox/.gitkeep": "",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def make_vault(root: Path) -> tuple[Path, Path, Path]:
    origin, laptop, worker = root / "origin.git", root / "laptop", root / "worker"
    subprocess.run(["git", "init", "--quiet", "--bare", "--initial-branch=main", str(origin)], check=True)
    subprocess.run(["git", "clone", "--quiet", str(origin), str(laptop)], check=True, capture_output=True)
    git(laptop, "config", "user.name", "Zac")
    git(laptop, "config", "user.email", "zac@example.invalid")
    for name, text in SEED.items():
        path = laptop / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(laptop, "add", "--all")
    git(laptop, "commit", "--quiet", "--message", "seed")
    git(laptop, "push", "--quiet", "origin", "main")
    subprocess.run(["git", "clone", "--quiet", str(origin), str(worker)], check=True, capture_output=True)
    return origin, laptop, worker


def laptop_push(laptop: Path, name: str, text: str) -> None:
    path = laptop / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    git(laptop, "add", "--all")
    git(laptop, "commit", "--quiet", "--message", f"edit {name}")
    git(laptop, "push", "--quiet", "origin", "main")


def show(origin: Path, name: str) -> str:
    return git(origin, "show", f"HEAD:{name}")
