from __future__ import annotations

import json
import warnings
from typing import Annotated

import typer

from backfills._options import ApplyOption, OrganizationIdOption, feature_environment
from backfills.registry import Backfill, discover, get

warnings.filterwarnings("ignore", category=ResourceWarning)

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Schema-change backfills.")

JsonOption = Annotated[bool, typer.Option("--json", help="Print the catalogue as one JSON line.")]


def catalogue(backfills: list[Backfill]) -> str:
    return json.dumps(
        {"backfills": [{"name": backfill.name, "description": backfill.description} for backfill in backfills]}
    )


@app.command(name="list")
def list_backfills(as_json: JsonOption = False) -> None:
    """List the available schema-change backfills."""
    backfills = discover()
    if as_json:
        print(catalogue(backfills))
        return

    if not backfills:
        print("No backfills found.")
        return

    for backfill in backfills:
        print(f"{backfill.name}\n    {backfill.description}")


@app.command()
def run(
    name: Annotated[str, typer.Argument(help="Backfill name (see `backfill list`).")],
    apply: ApplyOption = False,
    organization_id: OrganizationIdOption = None,
) -> None:
    """Run a schema-change backfill. Defaults to a dry run; pass --apply to write."""
    backfill = get(name)
    environment = feature_environment()
    state = "apply" if apply else "dry-run"
    print(f"Backfill '{backfill.name}' — environment: {environment or 'production'} ({state})")
    backfill.run(environment=environment, apply=apply, organization_id=organization_id)
