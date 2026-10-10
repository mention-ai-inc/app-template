from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

CANONICALIZER = Path(__file__).resolve().parents[1] / "_helpers" / "canonicalize_openapi.py"


def canonicalize(spec: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(CANONICALIZER)], input=json.dumps(spec), text=True, capture_output=True
    )


def canonical(spec: dict[str, Any]) -> dict[str, Any]:
    result = canonicalize(spec)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def spec(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": "Unified API", "version": "0.1.0", "contact": {"name": "Nobody"}},
        "servers": [],
        "tags": [],
        "security": [],
        "paths": {
            "/rest/notes/notes": {
                "get": {
                    "operationId": "list_notes",
                    "tags": ["Notes"],
                    "parameters": [],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ListNotesResponse", "title": "Notes"}
                                }
                            },
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "ListNotesResponse": {
                    "title": "ListNotesResponse",
                    "type": "object",
                    "required": ["notes", "cursor"],
                    "properties": {
                        "notes": {
                            "title": "Notes",
                            "description": "The notes",
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "cursor": {"title": "Cursor", "type": "string", "nullable": True},
                        "mode": {"title": "Mode", "type": "string", "enum": ["full"]},
                        "owner": {"title": "Owner", "type": ["string", "null"], "format": "uuid"},
                    },
                }
            },
            "securitySchemes": {},
            "parameters": {},
        },
    }
    base.update(overrides)
    return base


def test_output_is_sorted_two_space_indented_json_with_a_trailing_newline() -> None:
    result = canonicalize(spec())

    assert result.returncode == 0, result.stderr
    assert result.stdout == json.dumps(json.loads(result.stdout), indent=2, sort_keys=True) + "\n"
    assert list(json.loads(result.stdout)["components"]["schemas"]["ListNotesResponse"]["required"]) == [
        "cursor",
        "notes",
    ]


def test_empty_collections_and_the_contact_are_dropped() -> None:
    document = canonical(spec())

    assert "servers" not in document
    assert "tags" not in document
    assert "security" not in document
    assert "contact" not in document["info"]
    assert set(document["components"]) == {"schemas"}
    assert "parameters" not in document["paths"]["/rest/notes/notes"]["get"]


def test_titles_and_property_descriptions_are_stripped() -> None:
    schema = canonical(spec())["components"]["schemas"]["ListNotesResponse"]

    assert "title" not in schema
    assert "title" not in schema["properties"]["notes"]
    assert "description" not in schema["properties"]["notes"]


def test_schema_descriptions_survive() -> None:
    document = spec()
    document["components"]["schemas"]["ListNotesResponse"]["description"] = "A page of notes"

    schema = canonical(document)["components"]["schemas"]["ListNotesResponse"]

    assert schema["description"] == "A page of notes"


def test_nullable_becomes_an_any_of_with_null() -> None:
    properties = canonical(spec())["components"]["schemas"]["ListNotesResponse"]["properties"]

    assert properties["cursor"] == {"anyOf": [{"type": "string"}, {"type": "null"}]}
    assert properties["owner"] == {"anyOf": [{"type": "string", "format": "uuid"}, {"type": "null"}]}


def test_a_single_value_enum_becomes_a_const() -> None:
    properties = canonical(spec())["components"]["schemas"]["ListNotesResponse"]["properties"]

    assert properties["mode"] == {"type": "string", "const": "full"}


def test_reference_titles_inside_responses_are_stripped() -> None:
    response = canonical(spec())["paths"]["/rest/notes/notes"]["get"]["responses"]["200"]

    assert response["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/ListNotesResponse"}


def test_components_vanish_when_nothing_is_left() -> None:
    document = canonical(spec(components={"schemas": {}, "securitySchemes": {}}))

    assert "components" not in document


@pytest.mark.parametrize("name", ["notes__models__NoteRead", "a__b"])
def test_module_qualified_schema_names_are_refused(name: str) -> None:
    document = spec()
    document["components"]["schemas"][name] = {"type": "object"}

    result = canonicalize(document)

    assert result.returncode == 1
    assert name in result.stderr


def test_duplicate_operation_ids_are_refused() -> None:
    document = spec()
    document["paths"]["/rest/notes/other"] = {"post": dict(document["paths"]["/rest/notes/notes"]["get"])}

    result = canonicalize(document)

    assert result.returncode == 1
    assert "list_notes" in result.stderr


def test_canonicalization_is_idempotent() -> None:
    once = canonical(spec())

    assert canonical(once) == once
