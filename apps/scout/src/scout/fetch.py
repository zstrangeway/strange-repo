"""Getting a posting out of a URL.

The fetch is ours and the extraction is trafilatura's. Doing the fetch here
rather than letting trafilatura do it is deliberate: it collapses every
failure into ``None``, and "the board answered 403" and "the page had no
posting in it" need different sentences, because they need different things
from the person reading them.
"""

import os

import httpx
import trafilatura

from .errors import ScoutError

# A real posting is a few thousand characters. Anything under this is a cookie
# banner, a login wall, or the shell of a page whose content arrives by
# JavaScript — and a posting saved as a cookie banner is worse than one never
# saved, because tailoring will read it and produce something confident.
MINIMUM_POSTING = 400

# Length alone does not tell a job from a list of jobs. A board's index page
# is long, extracts cleanly, and is not a posting — and one saved as a posting
# is the same failure as the cookie banner, just harder to notice.
#
# What separates them is prose. Measured against real pages: Greenhouse's
# board index extracted to 3.2k characters holding **one** sentence, and
# python.org's job list to 3.9k holding **none**, while an individual posting
# on that same Greenhouse board held **31**. A job describes itself in
# paragraphs; an index is titles and locations.
#
# So the bar is deliberately at the bottom of that gap rather than in the
# middle of it: refuse only a page with at most one sentence in it. A terse
# posting stays saveable, and pasting always works regardless.
MINIMUM_SENTENCES = 2

# Long enough not to be a heading, and ending the way a sentence ends.
SENTENCE = 60

# Boards serve different HTML to something that announces itself as a script.
# This is not evasion — it is the same page a person would see, and the fetch
# stops at the first refusal rather than trying again from another angle.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

PASTE_INSTEAD = (
    'Paste the text instead: scout save --text "$(pbpaste)", or '
    "scout save --text - to read it from stdin."
)


def _sentences(text: str) -> int:
    """How many lines read as prose rather than as a link in a list."""
    return sum(
        1
        for line in text.splitlines()
        if len(line.strip()) >= SENTENCE and line.strip().endswith((".", "!", "?"))
    )


def posting_from_url(
    url: str, *, timeout: float | None = None
) -> tuple[str, str | None]:
    """Fetch ``url`` and return its posting text and title.

    Raises ``ScoutError`` with something actionable for every way this fails,
    rather than returning an empty posting.
    """
    # Overridable so the specs can stand up a board that never answers without
    # sitting there for fifteen seconds proving it.
    if timeout is None:
        timeout = float(os.environ.get("SCOUT_FETCH_TIMEOUT", "15"))
    try:
        response = httpx.get(
            url, headers=HEADERS, timeout=timeout, follow_redirects=True
        )
    except httpx.TimeoutException as exc:
        raise ScoutError(
            f"The fetch timed out after {timeout:g}s: {url}", detail=PASTE_INSTEAD
        ) from exc
    except httpx.HTTPError as exc:
        raise ScoutError(f"Could not reach {url}: {exc}", detail=PASTE_INSTEAD) from exc

    if response.status_code >= 400:
        raise ScoutError(
            f"The board refused the fetch: {response.status_code} from {url}.",
            detail=(
                "Boards behind a login or a bot check answer this way. " + PASTE_INSTEAD
            ),
        )

    text = trafilatura.extract(response.text, url=url, favor_recall=True)
    if text is None or len(text.strip()) < MINIMUM_POSTING:
        raise ScoutError(
            f"There was no readable posting in {url}.",
            detail=(
                "The page was fetched, but what came back was too short to be "
                "a posting — usually a login wall, or a shell that fills "
                "itself in with JavaScript. " + PASTE_INSTEAD
            ),
        )

    if _sentences(text) < MINIMUM_SENTENCES:
        raise ScoutError(
            f"That looks like a list of jobs rather than one posting: {url}",
            detail=(
                "Open the posting itself and save its URL instead — a board's "
                "index has the titles but not the job, and a resume tailored "
                "to a list of titles is worse than no resume. If this really "
                "is one posting, " + PASTE_INSTEAD[0].lower() + PASTE_INSTEAD[1:]
            ),
        )

    metadata = trafilatura.extract_metadata(response.text)
    title = metadata.title if metadata is not None else None
    return text.strip(), title
