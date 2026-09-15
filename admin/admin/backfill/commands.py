"""Typer commands for discovering and running schema-change backfills.

Backfills legitimately target production (empty `FEATURE_ENVIRONMENT`), so `run` reads the
environment without the feature-only guard the seed uses. Outside the job container the commands
launch `admin-j-backfill` through the cloud provider and follow its execution.
"""

from __future__ import annotations

from typing import Annotated

import typer

from admin.backfill.registry import discover, get
from admin.client.api import deployed_job_image, launch_and_follow, runs_in_job
from admin.common.environment import feature_environment
from admin.common.options import ApplyOption, run_async

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command(name="list")
def list_backfills() -> None:
    """List the available schema-change backfills."""
    backfills = discover()
    if not backfills:
        print("No backfills found.")
        return

    if not runs_in_job():
        image = run_async(deployed_job_image(group="backfill"))
        print(f"Deployed image: {image or 'not deployed yet'}")

    for backfill in backfills:
        print(f"{backfill.name}\n    {backfill.description}")


@app.command()
def run(
    name: Annotated[str, typer.Argument(help="Backfill name (see `backfill list`).")],
    apply: ApplyOption = False,
    organization_id: Annotated[str | None, typer.Option("--organization-id", help="Limit to one organization.")] = None,
) -> None:
    """Run a schema-change backfill. Defaults to a dry run; pass --apply to write."""
    if runs_in_job():
        backfill = get(name)
        environment = feature_environment()
        state = "apply" if apply else "dry-run"
        print(f"Backfill '{backfill.name}' — environment: {environment or 'production'} ({state})")
        backfill.run(environment=environment, apply=apply, organization_id=organization_id)
        return

    get(name)
    print(f"Backfill '{name}' — environment: {feature_environment() or 'production'}")
    args = ["run", name]
    if apply:
        args.append("--apply")
    if organization_id is not None:
        args.extend(["--organization-id", organization_id])
    run_async(
        launch_and_follow(
            group="backfill",
            operation="backfill.run",
            args=args,
            organization_id=organization_id,
            parameters={"backfill": name, "apply": apply},
        )
    )
