import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

EMPTY_ROOT_KEYS = ("servers", "tags", "security")
EMPTY_OPERATION_KEYS = ("tags", "security", "parameters")
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
SCHEMA_LIST_KEYS = ("anyOf", "oneOf", "allOf", "prefixItems")
SCHEMA_SINGLE_KEYS = ("items", "not", "additionalProperties", "propertyNames", "contains")
SCHEMA_MAP_KEYS = ("$defs", "definitions", "patternProperties")
NULL_TYPE = {"type": "null"}


class ContractError(Exception):
    pass


def canonicalize(spec: dict[str, Any]) -> dict[str, Any]:
    spec = json.loads(json.dumps(spec))
    __check_schema_names(spec)
    __check_operation_ids(spec)
    cast(dict[str, Any], spec.get("info", {})).pop("contact", None)
    __canonicalize_paths(spec)
    __canonicalize_components(spec)
    __drop_empty(spec, EMPTY_ROOT_KEYS)
    return spec


def render(spec: dict[str, Any]) -> str:
    return json.dumps(canonicalize(spec), indent=2, sort_keys=True) + "\n"


def __check_schema_names(spec: dict[str, Any]) -> None:
    schemas = cast(dict[str, Any], spec.get("components", {}).get("schemas", {}))
    mangled = sorted(name for name in schemas if "__" in name)
    if mangled:
        raise ContractError(
            "Schema names must be unique class names, got module-qualified names: " + ", ".join(mangled)
        )


def __check_operation_ids(spec: dict[str, Any]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for operation in __operations(spec):
        operation_id = cast(str | None, operation.get("operationId"))
        if operation_id is None:
            raise ContractError("Every operation needs an operationId")
        if operation_id in seen:
            duplicates.add(operation_id)
        seen.add(operation_id)
    if duplicates:
        raise ContractError("Duplicate operationIds: " + ", ".join(sorted(duplicates)))


def __operations(spec: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for path_item in cast(dict[str, dict[str, Any]], spec.get("paths", {})).values():
        operations.extend(path_item[method] for method in HTTP_METHODS if method in path_item)
    return operations


def __canonicalize_paths(spec: dict[str, Any]) -> None:
    for operation in __operations(spec):
        for parameter in cast(list[dict[str, Any]], operation.get("parameters", [])):
            if "schema" in parameter:
                parameter["schema"] = __canonicalize_schema(parameter["schema"], is_property=False)
        __canonicalize_content(cast(dict[str, Any], operation.get("requestBody", {})))
        for response in cast(dict[str, dict[str, Any]], operation.get("responses", {})).values():
            __canonicalize_content(response)
        __drop_empty(operation, EMPTY_OPERATION_KEYS)


def __canonicalize_content(holder: dict[str, Any]) -> None:
    for media in cast(dict[str, dict[str, Any]], holder.get("content", {})).values():
        if "schema" in media:
            media["schema"] = __canonicalize_schema(media["schema"], is_property=False)


def __canonicalize_components(spec: dict[str, Any]) -> None:
    components = cast(dict[str, dict[str, Any]], spec.get("components", {}))
    schemas = components.get("schemas", {})
    for name, schema in schemas.items():
        schemas[name] = __canonicalize_schema(schema, is_property=False)
    for name in [name for name, entries in components.items() if not entries]:
        del components[name]
    if "components" in spec and not components:
        del spec["components"]


def __canonicalize_schema(schema: Any, *, is_property: bool) -> Any:
    if not isinstance(schema, dict):
        return schema
    schema = cast(dict[str, Any], schema)
    schema.pop("title", None)
    if is_property:
        schema.pop("description", None)
    if "required" in schema and isinstance(schema["required"], list):
        schema["required"] = sorted(cast(list[str], schema["required"]))
    if "enum" in schema and isinstance(schema["enum"], list) and len(cast(list[Any], schema["enum"])) == 1:
        schema["const"] = cast(list[Any], schema.pop("enum"))[0]
    for key, value in cast(dict[str, Any], schema.get("properties", {})).items():
        schema["properties"][key] = __canonicalize_schema(value, is_property=True)
    for key in SCHEMA_MAP_KEYS:
        for name, value in cast(dict[str, Any], schema.get(key, {})).items():
            schema[key][name] = __canonicalize_schema(value, is_property=False)
    for key in SCHEMA_LIST_KEYS:
        if key in schema:
            schema[key] = [__canonicalize_schema(entry, is_property=is_property) for entry in schema[key]]
    for key in SCHEMA_SINGLE_KEYS:
        if key in schema:
            schema[key] = __canonicalize_schema(schema[key], is_property=is_property)
    return __canonicalize_nullable(schema)


def __canonicalize_nullable(schema: dict[str, Any]) -> dict[str, Any]:
    nullable = schema.pop("nullable", False) is True
    types = schema.get("type")
    if isinstance(types, list):
        types = cast(list[str], types)
        remaining = [entry for entry in types if entry != "null"]
        nullable = nullable or len(remaining) < len(types)
        if len(remaining) == 1:
            schema["type"] = remaining[0]
        else:
            schema["type"] = remaining
    if not nullable:
        return schema
    if "anyOf" in schema:
        variants = cast(list[dict[str, Any]], schema["anyOf"])
        if NULL_TYPE not in variants:
            variants.append(dict(NULL_TYPE))
        return schema
    return {"anyOf": [schema, dict(NULL_TYPE)]}


def __drop_empty(holder: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key in holder and not holder[key]:
            del holder[key]


def main() -> None:
    parser = argparse.ArgumentParser(description="Canonicalize an OpenAPI document read from stdin.")
    parser.add_argument("--output", type=Path, default=None, help="Write here instead of stdout.")
    arguments = parser.parse_args()
    try:
        rendered = render(json.load(sys.stdin))
    except json.JSONDecodeError as error:
        print(f"The generator did not print an OpenAPI document: {error}", file=sys.stderr)
        sys.exit(1)
    except ContractError as error:
        print(f"OpenAPI contract error: {error}", file=sys.stderr)
        sys.exit(1)
    if arguments.output is None:
        sys.stdout.write(rendered)
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered)


if __name__ == "__main__":
    main()
