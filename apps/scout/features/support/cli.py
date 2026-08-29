"""Running scout the way a person does, and the fixtures behind it.

The CLI is called in-process rather than as a subprocess: it is the same code
either way, and in-process is what lets one coverage run see both these specs
and the unit tests. The MCP server is the exception — see `support/mcp.py`.
"""

import contextlib
import io
from pathlib import Path

from scout import cli

MASTER = """# Ada Lovelace

## Skills

{skills}

## Experience

### {first} — Senior Engineer

2021–2025

- Cut deploy time from 40 minutes to 4, on Postgres and Terraform
- Led a team of 3 through the billing migration
- Ran the release process every week

### {second} — Platform Engineer

2018–2021

- Built the Python services behind billing
- Owned the Postgres upgrade
"""


def run(context, *argv):
    """Call scout and keep everything it said."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        context.exit_code = cli.main([str(argument) for argument in argv])
    context.stdout = out.getvalue()
    context.stderr = err.getvalue()
    # Steps assert against both together: which stream a sentence came out of
    # is a separate scenario, and asserting it everywhere would make every
    # other scenario care.
    context.output = context.stdout + context.stderr
    return context.output


def resumes_dir(context) -> Path:
    return context.home / "resumes"


def write_master(
    context,
    first="Wilding Labs",
    second="Thornfield Systems",
    skills="Python, Postgres, Terraform",
):
    directory = resumes_dir(context)
    directory.mkdir(parents=True, exist_ok=True)
    text = MASTER.format(first=first, second=second, skills=skills)
    (directory / "master.md").write_text(text, encoding="utf-8")
    context.master = text
    context.employers = (first, second)
    return text


def set_draft(context, draft: str) -> None:
    """What the stubbed provider will return.

    A file rather than an environment variable: the MCP specs drive a server
    that was started before the scenario decided what the model should say,
    and a running process cannot be told after the fact.
    """
    directory = context.home / ".scout"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "fake-draft.md").write_text(draft, encoding="utf-8")


def tailored(context, ref: str, version: int) -> Path:
    return resumes_dir(context) / ref / f"v{version}.md"


def only_ref(context) -> str:
    """The reference of the posting a scenario has been talking about."""
    return context.ref
