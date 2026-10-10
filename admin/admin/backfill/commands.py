"""Typer launchers for the schema-change backfills.

The backfills themselves live in the language slot's `backfills` image, not in admin. `list` asks the
deployed job for its catalogue and `run` launches the job with the bare `backfill` arguments, then
follows the execution to a terminal status. Backfills legitimately target production (empty
`FEATURE_ENVIRONMENT`), so neither command applies the feature-only guard the seed uses.
"""

from __future__ import annotations

from typing import Annotated

import typer

from admin.client.api import deployed_job_image, launch_and_follow
from admin.client.api import list_backfills as deployed_backfills
from admin.common.environment import feature_environment
from admin.common.options import ApplyOption, run_async
from admin.server.catalogue import BACKFILL_GROUP

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command(name="list")
def list_backfills() -> None:
    """List the backfills in the deployed image."""
    image = run_async(deployed_job_image(group=BACKFILL_GROUP))
    print(f"Deployed image: {image or 'not deployed yet'}")

    backfills = run_async(deployed_backfills())
    if not backfills:
        print("No backfills found.")
        return

    for backfill in backfills:
        print(f"{backfill.name}\n    {backfill.description}")


@app.command()
def run(
    name: Annotated[str, typer.Argument(help="Backfill name (see `backfill list`).")],
    apply: ApplyOption = False,
    organization_id: Annotated[str | None, typer.Option("--organization-id", help="Limit to one organization.")] = None,
) -> None:
    """Run a schema-change backfill. Defaults to a dry run; pass --apply to write."""
    print(f"Backfill '{name}' — environment: {feature_environment() or 'production'}")
    args = ["run", name]
    if apply:
        args.append("--apply")
    if organization_id is not None:
        args.extend(["--organization-id", organization_id])
    run_async(
        launch_and_follow(
            group=BACKFILL_GROUP,
            operation="backfill.run",
            args=args,
            organization_id=organization_id,
            parameters={"backfill": name, "apply": apply},
        )
    )
