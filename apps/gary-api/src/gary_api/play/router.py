"""The FastAPI router for play endpoints.

Kept in its own module so every route module can import it without
creating circular imports.
"""

from fastapi import APIRouter

router = APIRouter(tags=["play"])
