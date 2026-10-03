"""Each scenario gets fresh repositories in its own directory, so no
scenario can pass because of one that ran before it."""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from support_repos import make_vault


def before_scenario(context, scenario):
    context.root = Path(tempfile.mkdtemp(prefix="vault-sync-"))
    context.origin, context.laptop, context.worker = make_vault(context.root)
    context.written = {}


def after_scenario(context, scenario):
    shutil.rmtree(context.root, ignore_errors=True)
