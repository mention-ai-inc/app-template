from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


class VerificationError(Exception):
    pass


@firestore.transactional
def retry_command(
    transaction: firestore.Transaction,
    note_reference: firestore.DocumentReference,
    command_reference: firestore.DocumentReference,
    organization_id: str,
    note_id: str,
) -> None:
    note = note_reference.get(transaction=transaction).to_dict() or {}
    command = command_reference.get(transaction=transaction).to_dict() or {}
    if note.get("status") != "summarizing" or note.get("summary") is not None:
        raise VerificationError("The note is no longer awaiting a summary.")
    if (
        command.get("organization_id") != organization_id
        or command.get("payload", {}).get("note_id") != note_id
        or command.get("name") != "SummarizeNote"
        or command.get("processed_at") is not None
        or command.get("dispatched_at") is None
    ):
        raise VerificationError("The command is not eligible for redispatch.")
    transaction.update(command_reference, {"dispatched_at": None})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--note-id", required=True)
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--environment", default=os.environ.get("FEATURE_ENVIRONMENT", "demo"))
    args = parser.parse_args()
    if not re.fullmatch(r"org_[A-Za-z0-9]+", args.organization_id) or not re.fullmatch(r"[A-Za-z0-9_-]+", args.note_id):
        raise VerificationError("Invalid organization or note identifier.")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", args.environment) or args.environment == "production":
        raise VerificationError("An explicit non-production feature environment is required.")
    config = json.loads(Path("project.json").read_text())
    project_id = config["cloud_values"]["feature_project_id"]
    if not project_id or project_id == config["cloud_values"]["production_project_id"]:
        raise VerificationError("A distinct feature project is required.")
    client = firestore.Client(project=project_id)
    note_reference = client.collection(f"{args.environment}notes_{args.organization_id}_note").document(args.note_id)
    note_snapshot = note_reference.get(field_paths=["status", "summary", "organization_id"])
    if not note_snapshot.exists:
        raise VerificationError("The specified demo note does not exist.")
    note = note_snapshot.to_dict() or {}
    if note.get("organization_id") != args.organization_id:
        raise VerificationError("The note belongs to a different organization.")
    summary = note.get("summary")
    print(
        json.dumps(
            {
                "environment": args.environment,
                "status": note.get("status"),
                "summary_present": isinstance(summary, str) and bool(summary.strip()),
                "summary_characters": len(summary) if isinstance(summary, str) else 0,
            }
        )
    )
    commands = list(
        client.collection(f"{args.environment}notes_commands")
        .where(filter=FieldFilter("payload.note_id", "==", args.note_id))
        .select(["organization_id", "name", "dispatched_at", "processed_at", "success", "attempt_count"])
        .limit(10)
        .stream()
    )
    eligible: list[str] = []
    for command_snapshot in commands:
        command = command_snapshot.to_dict() or {}
        if command.get("organization_id") != args.organization_id or command.get("name") != "SummarizeNote":
            continue
        print(
            json.dumps(
                {
                    "command": "SummarizeNote",
                    "dispatched": command.get("dispatched_at") is not None,
                    "processed": command.get("processed_at") is not None,
                    "success": command.get("success"),
                    "attempt_count": command.get("attempt_count"),
                }
            )
        )
        if command.get("dispatched_at") is not None and command.get("processed_at") is None:
            eligible.append(command_snapshot.id)
    if args.retry:
        if len(eligible) != 1:
            raise VerificationError("Retry requires exactly one dispatched, unprocessed summary command.")
        command_reference = client.collection(f"{args.environment}notes_commands").document(eligible[0])
        retry_command(client.transaction(), note_reference, command_reference, args.organization_id, args.note_id)
        print("Redispatch requested through the existing feature command trigger.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except VerificationError as error:
        print(f"BLOCKED {error}")
        sys.exit(1)
    except Exception as error:
        print(f"BLOCKED demo note operation failed ({type(error).__name__}); payloads withheld.")
        sys.exit(1)
