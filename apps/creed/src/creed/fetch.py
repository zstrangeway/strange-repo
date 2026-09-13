"""Talking to Wahapedia, and nothing else.

Kept apart from sync.py so that the specs can drive a sync against a stub
without a network, and so the one place that makes requests is the one place
to look when the answers are stale.

Conditional GET is the whole point. Every file in the export carries an ETag
and a Last-Modified and the origin honours both, so a re-sync after a
dataslate pays for the handful of files that moved rather than for all 8.4MB.
"""

from dataclasses import dataclass

import httpx

from . import export

# The export is static files behind a CDN. Long enough that a slow transfer of
# the 2.1MB stratagems table finishes, short enough that a dead network is a
# failed sync rather than a hung command.
TIMEOUT_SECONDS = 30.0

USER_AGENT = f"creed/{__import__('creed').__version__} (+https://wahapedia.ru)"


class ExportUnreachableError(Exception):
    """The export could not be reached at all.

    Distinct from a malformed table on purpose: one means try again later and
    the other means the export changed shape. Collapsing them into one error
    is how "we are offline" comes to read as "the data is broken".
    """


@dataclass(frozen=True)
class Response:
    """What one conditional GET came back with."""

    text: str | None
    etag: str | None
    last_modified: str | None
    not_modified: bool

    @property
    def changed(self) -> bool:
        return not self.not_modified


@dataclass(frozen=True)
class Validators:
    etag: str | None = None
    last_modified: str | None = None


class Fetcher:
    """Fetches export tables, passing conditional-GET validators through."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client
        self._owned = client is None

    def __enter__(self) -> "Fetcher":
        if self._client is None:
            self._client = httpx.Client(
                timeout=TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._owned and self._client is not None:
            self._client.close()
            self._client = None

    def get(self, table: export.Table, validators: Validators) -> Response:
        headers = {}
        if validators.etag:
            headers["If-None-Match"] = validators.etag
        if validators.last_modified:
            headers["If-Modified-Since"] = validators.last_modified
        try:
            response = self._client.get(table.url, headers=headers)
        except httpx.HTTPError as error:
            raise ExportUnreachableError(f"{table.name}: {error}") from error
        if response.status_code == httpx.codes.NOT_MODIFIED:
            return Response(
                text=None,
                etag=validators.etag,
                last_modified=validators.last_modified,
                not_modified=True,
            )
        if response.status_code != httpx.codes.OK:
            raise ExportUnreachableError(
                f"{table.name}: the export answered {response.status_code}"
            )
        return Response(
            # Decoded from bytes rather than taken as .text, so the BOM the
            # export leads with is consumed instead of becoming part of the
            # first column's name.
            text=response.content.decode(export.ENCODING),
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
            not_modified=False,
        )
