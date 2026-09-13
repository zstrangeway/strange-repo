"""The envelope every answer travels in.

A model reading a tool result cannot see the sync log. If an answer does not
carry its own date, the model has no way to tell somebody "this is from before
the September dataslate", and "never stale" becomes a claim nobody can check
from the outside. So the date rides along with every answer rather than being
available from a separate call somebody has to think to make.

The attribution rides along for the same reason, and because the export's own
terms ask for it.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from . import db, export, sync

# Past this, an answer says so. The export moves within about fifteen minutes
# of a site edit and a dataslate is a monthly event, so a week without a
# successful check means something is wrong with the checking rather than that
# nothing has happened.
STALE_AFTER_DAYS = 7


class NotSyncedError(Exception):
    """There is no data yet.

    Its own error because an empty result and an empty database read
    identically to a caller, and the difference is between "that unit does not
    exist" and "creed has not started yet".
    """


@dataclass
class Provenance:
    """Where an answer came from and how far behind it might be."""

    last_update: str
    last_checked: str | None = None
    warnings: list[str] = field(default_factory=list)
    attribution: str = export.ATTRIBUTION

    def as_dict(self) -> dict[str, object]:
        return {
            "data_as_of": self.last_update,
            "last_checked": self.last_checked,
            "warnings": list(self.warnings),
            "source": self.attribution,
        }


def _age_in_days(stamp: str | None) -> float | None:
    if not stamp:
        return None
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return (datetime.now(UTC) - when).total_seconds() / 86400


def provenance(connection) -> Provenance:
    """Read the sync state, refusing to answer at all when there is none."""
    last_update = db.get_state(connection, sync.LAST_UPDATE_KEY)
    if last_update is None:
        raise NotSyncedError(
            "creed has no data yet. Run `creed sync` to pull the current "
            "Wahapedia export."
        )
    last_checked = db.get_state(connection, sync.LAST_CHECKED_KEY)
    warnings = []
    age = _age_in_days(last_checked)
    if age is not None and age > STALE_AFTER_DAYS:
        warnings.append(
            f"creed last reached the export {age:.0f} days ago, so this may be "
            "behind a dataslate. Run `creed sync`."
        )
    return Provenance(
        last_update=last_update, last_checked=last_checked, warnings=warnings
    )
