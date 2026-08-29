"""The command line.

Every command is the same three steps: open the database, call the capability,
print what it returned. The capabilities are in their own modules and know
nothing about argv, which is what lets the MCP server be a second surface onto
them rather than a second implementation of them.
"""

import argparse
import sys

from . import applications, db, example, paths, postings, tailoring
from .errors import ScoutError
from .providers import load as load_provider


def _read_text(value: str) -> str:
    """`--text -` reads stdin, so a posting can be piped in."""
    return sys.stdin.read() if value == "-" else value


def _init(args: argparse.Namespace) -> int:
    """Make the directory scout works in, and say what it did.

    A setup step that silently does nothing is worse than no setup step, so
    this one names every file it wrote and every file it left alone.
    """
    resumes = paths.resumes_dir()
    resumes.mkdir(parents=True, exist_ok=True)
    print(f"Working in {paths.home()}")

    sample = resumes / "master.example.md"
    sample.write_text(example.GUIDANCE + example.MASTER, encoding="utf-8")
    print(f"  wrote   {sample.relative_to(paths.home())}")

    master = paths.master_resume_path()
    if master.exists():
        print(f"  kept    {master.relative_to(paths.home())} (already there)")
    else:
        master.write_text(example.GUIDANCE + example.MASTER, encoding="utf-8")
        print(f"  wrote   {master.relative_to(paths.home())} — replace it with yours")
    return 0


def _save(args: argparse.Namespace) -> int:
    with db.connect() as connection:
        posting = postings.save(
            connection,
            text=_read_text(args.text) if args.text else None,
            url=args.url,
            title=args.title,
            company=args.company,
        )
    print(f"Saved {posting.ref}")
    if posting.title:
        print(f"  {posting.title}")
    if posting.company is None:
        # Said out loud rather than left blank in a listing somebody reads
        # weeks later and cannot explain.
        print(
            "  Company unknown — scout does not guess it. Set it with:\n"
            f'    scout edit {posting.ref} --company "..."'
        )
    return 0


def _list(args: argparse.Namespace) -> int:
    with db.connect() as connection:
        found = postings.all_postings(connection, in_play_only=args.in_play)
        if not found:
            print("Nothing saved yet. Start with: scout save --url ...")
            return 0
        for posting in found:
            status = applications.current_status(connection, posting.id)
            moved = applications.last_moved(connection, posting.id)
            title = posting.title or "(untitled)"
            print(
                f"{posting.ref:<32} {status:<10} {moved[:10]}  "
                f"{title} — {posting.company_or_unknown}"
            )
    return 0


def _show(args: argparse.Namespace) -> int:
    with db.connect() as connection:
        posting = postings.read(connection, args.ref)
        print(f"{posting.ref}")
        print(f"  title    {posting.title or '(untitled)'}")
        print(f"  company  {posting.company_or_unknown}")
        print(f"  status   {applications.current_status(connection, posting.id)}")
        if posting.source_url:
            print(f"  url      {posting.source_url}")
        print("\nHistory")
        for event in applications.history(connection, posting.id):
            marker = event.status or "note"
            print(f"  {event.at}  {marker:<10} {event.note or ''}".rstrip())
        print("\nPosting\n")
        print(posting.body)
    return 0


def _edit(args: argparse.Namespace) -> int:
    with db.connect() as connection:
        posting = postings.edit(
            connection, args.ref, title=args.title, company=args.company
        )
    print(f"Updated {posting.ref}")
    return 0


def _tailor(args: argparse.Namespace) -> int:
    with db.connect() as connection:
        result = tailoring.tailor(connection, args.ref, load_provider(args.provider))
    print(result.render())
    return 0


def _log(args: argparse.Namespace) -> int:
    with db.connect() as connection:
        posting = postings.read(connection, args.ref)
        current = applications.current_status(connection, posting.id)
        applications.check_transition(current, args.status)
        applications.record(connection, posting.id, args.status, args.note)
    print(f"{posting.ref} is now {args.status}")
    return 0


def _note(args: argparse.Namespace) -> int:
    with db.connect() as connection:
        posting = postings.read(connection, args.ref)
        applications.record(connection, posting.id, None, args.note)
    print(f"Noted against {posting.ref}")
    return 0


def _serve(args: argparse.Namespace) -> int:
    from .mcp_server import main as serve

    return serve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scout",
        description="A local-first, bring-your-own-model job search assistant.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    start = subcommands.add_parser(
        "init", help="Create resumes/ and an example master resume"
    )
    start.set_defaults(handler=_init)

    save = subcommands.add_parser("save", help="Save a job posting")
    source = save.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Fetch the posting from this URL")
    source.add_argument("--text", help="The posting itself, or - for stdin")
    save.add_argument("--title", help="The role, if scout should not guess")
    save.add_argument("--company", help="The company. Never guessed.")
    save.set_defaults(handler=_save)

    listing = subcommands.add_parser("list", help="List saved postings")
    listing.add_argument(
        "--in-play",
        action="store_true",
        help="Hide the ones that ended (rejected, ghosted)",
    )
    listing.set_defaults(handler=_list)

    show = subcommands.add_parser("show", help="Read one posting and its history")
    show.add_argument("ref")
    show.set_defaults(handler=_show)

    edit = subcommands.add_parser("edit", help="Set a posting's title or company")
    edit.add_argument("ref")
    edit.add_argument("--title")
    edit.add_argument("--company")
    edit.set_defaults(handler=_edit)

    tailor = subcommands.add_parser("tailor", help="Tailor your resume to a posting")
    tailor.add_argument("ref")
    tailor.add_argument(
        "--provider",
        default="anthropic",
        choices=("anthropic", "fake"),
        help=(
            "fake reads a draft from .scout/fake-draft.md instead of calling a "
            "model — what the specs drive, and a way to try scout with no key"
        ),
    )
    tailor.set_defaults(handler=_tailor)

    log = subcommands.add_parser("log", help="Log where an application got to")
    log.add_argument("ref")
    log.add_argument("status", help=", ".join(applications.STATUSES))
    log.add_argument("--note")
    log.set_defaults(handler=_log)

    note = subcommands.add_parser("note", help="Add a note without changing status")
    note.add_argument("ref")
    note.add_argument("note")
    note.set_defaults(handler=_note)

    serve = subcommands.add_parser("mcp", help="Run the MCP server over stdio")
    serve.set_defaults(handler=_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except ScoutError as error:
        # stderr, so that piping a command's output somewhere does not
        # silently swallow the reason it produced nothing.
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
