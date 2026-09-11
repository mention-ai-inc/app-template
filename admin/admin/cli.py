"""Root Typer app for the admin CLI.

Two operational concerns, one entrypoint (`m admin -- <group> <command> ...`):

- `seed` — seed a feature environment with an organization, a user, and a few notes.
- `backfill` — run schema-change migrations discovered under `admin/backfill/migrations/`.
"""

from __future__ import annotations

import warnings

import typer

from admin.backfill.commands import app as backfill_app
from admin.seed.commands import app as seed_app

warnings.filterwarnings("ignore", category=ResourceWarning)

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Admin operations.")
app.add_typer(seed_app, name="seed", help="Seed a feature environment.")
app.add_typer(backfill_app, name="backfill", help="Run schema-change backfills.")
