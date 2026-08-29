"""scout as an MCP server, over stdio.

The same capabilities the CLI calls, exposed as tools. Not a second
implementation of anything — every function here opens the database, calls the
module that does the work, and turns what comes back into text a model can
read.

Two rules this file exists to keep:

* **stdout is the protocol.** One stray print in a startup path and the
  client's first parse fails, which reaches a person as a server that will not
  connect and no explanation anywhere. Logging is pinned to stderr below.
* **A refusal is a result, not an exception.** An error crossing the transport
  takes the session's turn with it. Every tool catches ``ScoutError`` and
  returns it, so the model reads what went wrong and can fix its argument.
"""

import logging
import sys

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import applications, db, postings, tailoring
from .errors import ScoutError
from .providers import load as load_provider

logger = logging.getLogger("scout.mcp")

server = MCPServer(
    name="scout",
    instructions=(
        "A local-first job search assistant. Save a job posting, tailor the "
        "user's master resume to it, and log where the application got to. "
        "Tailoring may only reorder, reweight and rephrase what the master "
        "resume already says; a draft that invents an employer or a skill is "
        "refused and nothing is written."
    ),
)


def _failing(error: ScoutError) -> str:
    """Re-raise a refusal as the SDK's anticipated-failure exception.

    It has to be ``ToolError`` specifically. Any other exception is treated as
    a crash: the client is handed "Error executing tool <name>" and the reason
    is logged server-side, where nobody driving the tool will ever see it. The
    whole point of a refusal is that the model reads it and fixes its
    argument.
    """
    raise ToolError(str(error)) from error


@server.tool(
    description=(
        "Save a job posting from a URL or from pasted text. Pass exactly one "
        "of url or text. The company is never guessed — pass it if you know "
        "it. Returns the posting's reference, which every other tool takes."
    )
)
def save_posting(
    url: str | None = None,
    text: str | None = None,
    title: str | None = None,
    company: str | None = None,
) -> str:
    logger.info("tool.call save_posting")
    try:
        if (url is None) == (text is None):
            raise ScoutError("Pass exactly one of url or text.")
        with db.connect() as connection:
            posting = postings.save(
                connection, text=text, url=url, title=title, company=company
            )
        lines = [f"Saved {posting.ref}: {posting.title or '(untitled)'}"]
        if posting.company is None:
            lines.append(
                "The company is unknown — scout does not guess it. Set it "
                "with the edit command, or save again with company set."
            )
        return "\n".join(lines)
    except ScoutError as error:
        return _failing(error)


@server.tool(
    description=(
        "Tailor the user's master resume (resumes/master.md) to a saved "
        "posting and write it as a new version. The draft is checked against "
        "the master before anything is written: if it names an employer or "
        "claims a skill the master does not, nothing is written and the tool "
        "fails. Returns where the file went and what changed."
    )
)
def tailor_resume(ref: str, provider: str = "anthropic") -> str:
    logger.info("tool.call tailor_resume")
    try:
        with db.connect() as connection:
            result = tailoring.tailor(connection, ref, load_provider(provider))
        return result.render()
    except ScoutError as error:
        return _failing(error)


@server.tool(
    description=(
        "Log where an application got to. Statuses are saved, applied, "
        "screening, interview, offer, rejected, ghosted, and they follow that "
        "order — rejected and ghosted are reachable from anywhere. Pass a "
        "note to say why."
    )
)
def log_status(ref: str, status: str, note: str | None = None) -> str:
    logger.info("tool.call log_status")
    try:
        with db.connect() as connection:
            posting = postings.read(connection, ref)
            current = applications.current_status(connection, posting.id)
            applications.check_transition(current, status)
            applications.record(connection, posting.id, status, note)
        return f"{ref} is now {status}"
    except ScoutError as error:
        return _failing(error)


@server.tool(
    description=(
        "List saved postings, newest first, with each one's status and when "
        "it last moved. Set in_play_only to hide the ones that ended."
    )
)
def list_postings(in_play_only: bool = False) -> str:
    # No ScoutError guard, unlike the three above: reading a list cannot
    # refuse. An unreachable `except` claims a failure is handled when nothing
    # has ever handled one.
    logger.info("tool.call list_postings")
    with db.connect() as connection:
        found = postings.all_postings(connection, in_play_only=in_play_only)
        if not found:
            return "Nothing saved yet."
        return "\n".join(
            f"{posting.ref}  {applications.current_status(connection, posting.id)}"
            f"  {applications.last_moved(connection, posting.id)[:10]}"
            f"  {posting.title or '(untitled)'} — {posting.company_or_unknown}"
            for posting in found
        )


def main() -> int:
    """Run the server on stdio.

    Logging is configured before anything else can emit a record, and pinned
    to stderr: the default handler writes to stdout, which is the transport.
    """
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    )
    server.run("stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
