#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

arguments = sys.argv[1:]
state_path = Path(os.environ["FAKE_STATE"])
state: dict[str, Any] = json.loads(state_path.read_text()) if state_path.exists() else {"calls": [], "bindings": []}
state["calls"].append(arguments)
words = [argument for argument in arguments if not argument.startswith("--")]
mode = os.environ.get("FAKE_MODE", "")
result: object = {}
exit_code = 0


def option(name: str) -> str:
    return next(argument.split("=", 1)[1] for argument in arguments if argument.startswith(f"--{name}="))


if words[:2] == ["config", "list"]:
    result = {"core": {"account": "engineer@example.org"}}
elif words[:3] == ["billing", "accounts", "describe"]:
    result = {"open": True}
elif words[:3] == ["resource-manager", "folders", "list"]:
    folder = {"name": "folders/123456", "displayName": "example"}
    result = [folder, folder] if mode == "ambiguous" else ([folder] if state.get("folder") else [])
elif words[:3] == ["resource-manager", "folders", "create"]:
    state["folder"] = True
elif words[:2] == ["projects", "list"]:
    result = [{"projectId": "example-operations"}] if state.get("project") else []
elif words[:2] == ["projects", "create"]:
    state["project"] = True
    if mode == "interrupted":
        exit_code = 1
elif words[:2] == ["projects", "describe"]:
    result = {"parent": {"type": "folder", "id": "123456"}, "lifecycleState": "ACTIVE", "projectNumber": "123456789012"}
elif words[:3] == ["billing", "projects", "describe"]:
    result = {
        "billingEnabled": bool(state.get("billing")),
        "billingAccountName": "billingAccounts/other"
        if mode == "billing"
        else ("billingAccounts/AAAAAA-BBBBBB-CCCCCC" if state.get("billing") else ""),
    }
elif words[:3] == ["billing", "projects", "link"]:
    state["billing"] = True
elif words[:2] == ["services", "list"]:
    result = ""
elif words[:3] == ["storage", "buckets", "list"]:
    result = [{"name": "example-operations--terraform-state"}] if state.get("bucket") else []
elif words[:3] == ["storage", "buckets", "create"]:
    state["bucket"] = True
elif words[:3] == ["storage", "buckets", "describe"]:
    result = {
        "projectNumber": "999999999999" if mode == "bucket" else "123456789012",
        "location": "US-CENTRAL1",
        "versioning": {"enabled": bool(state.get("versioning"))},
    }
elif words[:3] == ["storage", "buckets", "update"]:
    state["versioning"] = True
elif words[:3] == ["iam", "service-accounts", "list"]:
    result = [{"email": "terraform@example-operations.iam.gserviceaccount.com"}] if state.get("identity") else []
elif words[:3] == ["iam", "service-accounts", "create"]:
    state["identity"] = True
elif "get-iam-policy" in words:
    result = {"bindings": state["bindings"]}
elif "add-iam-policy-binding" in words:
    state["bindings"].append({"role": option("role"), "members": [option("member")]})
elif words[:2] == ["auth", "print-access-token"]:
    result = "private-test-token"
    exit_code = int(mode == "identity_timeout")
state_path.write_text(json.dumps(state))
print(result if isinstance(result, str) else json.dumps(result))
sys.exit(exit_code)
