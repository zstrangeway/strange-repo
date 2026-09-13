"""Helpers the step files share.

They live here rather than in a step module because behave loads step files
with ``exec`` and no package context, so one step file cannot import another.
"""

from creed import sync


def synced(context, stamp: str | None = None):
    """Put a complete sync in place, from the scenario's own export site."""
    if stamp:
        context.site.set_last_update(stamp)
    context.result = sync.sync()
    assert context.result.failed is None, context.result.failed
    context.site.reset_requests()
    return context.result
