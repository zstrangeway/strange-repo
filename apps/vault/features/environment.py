"""Each scenario gets fresh repositories in its own directory, so no
scenario can pass because of one that ran before it."""

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from support_repos import make_vault

# Like the server: no git identity anywhere. Without this, a developer's own
# ~/.gitconfig supplies one and hides a sync that can't rebase in the pod.
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"


def before_scenario(context, scenario):
    context.root = Path(tempfile.mkdtemp(prefix="vault-sync-"))
    context.origin, context.laptop, context.worker = make_vault(context.root)
    context.written = {}


def after_scenario(context, scenario):
    shutil.rmtree(context.root, ignore_errors=True)
