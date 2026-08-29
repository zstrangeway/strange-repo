"""The one exception scout raises on purpose.

Everything a person can do wrong — a posting that is not there, a board that
refused the fetch, a draft that invented an employer — arrives as a
``ScoutError`` carrying a sentence meant to be read. The CLI prints it and
exits 1; the MCP server returns it as a failed tool result rather than letting
it out through the transport, because an exception crossing that boundary
takes the session's turn with it.
"""


class ScoutError(Exception):
    """Something the user can act on, phrased for the user."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        # Longer context printed under the message: the statuses that were
        # allowed, the draft that was refused. Kept apart from the message so
        # a caller can show one without the other.
        self.detail = detail

    def __str__(self) -> str:
        return (
            self.message if self.detail is None else f"{self.message}\n\n{self.detail}"
        )
