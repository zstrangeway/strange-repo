"""Where scout keeps things.

Everything is under one directory, so a job search is a folder somebody can
back up, move to another machine, or delete. ``SCOUT_HOME`` moves it; the
default is the working directory, which is what makes the quickstart a `cd`
and one command.
"""

import os
from pathlib import Path


def home() -> Path:
    """The directory scout works in."""
    return Path(os.environ.get("SCOUT_HOME", ".")).expanduser().resolve()


def database_path() -> Path:
    """The SQLite file. Created on first use, along with its directory."""
    return home() / ".scout" / "scout.db"


def resumes_dir() -> Path:
    """Where the master resume lives and where tailored ones are written."""
    return home() / "resumes"


def master_resume_path() -> Path:
    return resumes_dir() / "master.md"
