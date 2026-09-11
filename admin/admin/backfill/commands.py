"""Typer commands for discovering and running schema-change backfills.

Backfills legitimately target production (empty `FEATURE_ENVIRONMENT`), so `run` reads the
environment without the feature-only guard the seed uses. Outside the Cloud Run job the commands
call the admin API, which launches the `admin-j-backfill` job and reports its execution.
"""

from __future__ import annotations

from typing import Annotated

import typer

from admin.backfill.registry import discover, get
from admin.client.api import AdminClient, launch_and_follow, runs_in_job
from admin.common.environment import feature_environment
from admin.common.options import ApplyOption, run_async

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command(name="list")
def list_backfills() -> None:
    """List the available schema-change backfills."""
    if runs_in_job():
        backfills = discover()
        if not backfills:
            print("No backfills found.")
            return
        for backfill in backfills:
            print(f"{backfill.name}\n    {backfill.description}")
        return

    response = run_async(AdminClient().get("/backfills"))
    if response["image_digest"]:
        print(f"Deployed image: {response['image_digest']} (commit {response['commit_sha']})")
    for backfill_summary in response["backfills"]:
        print(f"{backfill_summary['name']}\n    {backfill_summary['description']}")


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

    print(f"Backfill '{name}' — environment: {feature_environment() or 'production'}")
    run_async(launch_and_follow(f"/backfills/{name}/runs", {"apply": apply, "organization_id": organization_id}))
