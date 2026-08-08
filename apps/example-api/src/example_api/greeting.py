"""Greeting rules shared by the API routes."""


def greet(name: str | None = None) -> str:
    """Build a greeting, falling back to "world" when no usable name is given."""
    trimmed = (name or "").strip()
    return f"Hello, {trimmed or 'world'}!"
