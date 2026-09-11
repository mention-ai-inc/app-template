"""Notes phase: create a few notes over the REST API as the seeded admin.

Creating a note triggers its summary server-side; nothing here waits for it. Idempotent: a note whose
title already exists in the organization is skipped, so a re-run adds nothing.
"""

from __future__ import annotations

from admin.common.logger import logger
from admin.seed.clients import SeedClient

NOTES = [
    {
        "title": "Welcome to the team",
        "body": "Introductions happen on Monday mornings. Bring one thing you learned last week and one question.",
    },
    {
        "title": "How we run retrospectives",
        "body": "Every second Friday. Start with what went well, then what to change, and end with one commitment.",
    },
    {
        "title": "Release checklist",
        "body": "Run the checks, update the docs, write the deployment plan, and ask before touching production.",
    },
]


async def run_notes_phase(*, client: SeedClient) -> None:
    existing_titles = {note["title"] for note in (await client.get("/notes"))["notes"]}

    created = 0
    for note in NOTES:
        if note["title"] in existing_titles:
            continue
        response = await client.post("/notes", json=note)
        created += 1
        logger.info("Created note %s (%s)", note["title"], response["id"])

    logger.info("Notes phase complete: %d created, %d already present.", created, len(NOTES) - created)
