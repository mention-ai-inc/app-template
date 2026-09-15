"""Typer commands for seeding a feature environment.

Outside the job container `run` launches `admin-j-seed` through the cloud provider and follows its
execution; inside the job it drives the seed directly.
"""

from __future__ import annotations

from typing import Annotated

import typer

from admin.client.api import launch_and_follow, runs_in_job
from admin.common.environment import SEED_ORGANIZATION_VARIABLE, default_seed_organization_id
from admin.common.options import run_async
from admin.seed.runner import run_seed

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def run(
    organization_id: Annotated[
        str | None,
        typer.Option(
            "--organization-id",
            help=f"Clerk organization id (org_...) to seed into. Defaults to {SEED_ORGANIZATION_VARIABLE}; "
            "when neither is set the seed creates an organization.",
        ),
    ] = None,
) -> None:
    """Seed the feature environment with an organization, an admin user, and a few notes."""
    resolved_organization_id = organization_id or default_seed_organization_id()
    if not runs_in_job():
        args = ["run"]
        if resolved_organization_id is not None:
            args.extend(["--organization-id", resolved_organization_id])
        run_async(
            launch_and_follow(
                group="seed",
                operation="seed.run",
                args=args,
                organization_id=resolved_organization_id,
                parameters={},
            )
        )
        return
    run_async(run_seed(organization_id=resolved_organization_id))
