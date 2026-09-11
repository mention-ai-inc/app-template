#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[3]
CANONICAL_ROOT = ROOT / ".agents"
CLAUDE_ROOT = ROOT / ".claude"
CURSOR_ROOT = ROOT / ".cursor"
SKILL_KEYS = {"name", "description"}


def render_claude_rule(body: str, paths: list[str]) -> str:
    if not paths:
        return body
    path_lines = "\n".join(f'  - "{path}"' for path in paths)
    return f"---\npaths:\n{path_lines}\n---\n\n{body}"


def render_cursor_rule(body: str, paths: list[str]) -> str:
    if paths:
        globs = ",".join(json.dumps(path) for path in paths)
        metadata = f"globs: {globs}\nalwaysApply: false"
    else:
        metadata = "alwaysApply: true"
    return f"---\n{metadata}\n---\n\n{body}"


def validate_skill(path: Path) -> None:
    lines = path.read_text().splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError(f"invalid skill frontmatter: {path.relative_to(ROOT)}")
    end = lines[1:].index("---") + 1
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator or not value.strip():
            raise ValueError(f"invalid skill metadata: {path.relative_to(ROOT)}")
        metadata[key] = value.strip()
    if set(metadata) != SKILL_KEYS:
        raise ValueError(f"skill metadata must contain only name and description: {path.relative_to(ROOT)}")
    if metadata["name"] != path.parent.name:
        raise ValueError(f"skill name must match its directory: {path.relative_to(ROOT)}")


def expected_files() -> dict[Path, bytes]:
    rules = cast(
        dict[str, list[str]],
        json.loads((CANONICAL_ROOT / "rules.json").read_text()),
    )
    rule_files = {path.stem: path for path in (CANONICAL_ROOT / "rules").glob("*.md")}
    if set(rules) != set(rule_files):
        missing = sorted(set(rules) - set(rule_files))
        extra = sorted(set(rule_files) - set(rules))
        raise ValueError(f"rules.json mismatch; missing={missing}, extra={extra}")

    expected = {ROOT / "CLAUDE.md": b"@AGENTS.md\n"}
    for name, paths in rules.items():
        body = rule_files[name].read_text()
        expected[CLAUDE_ROOT / "rules" / f"{name}.md"] = render_claude_rule(body, paths).encode()
        expected[CURSOR_ROOT / "rules" / f"{name}.mdc"] = render_cursor_rule(body, paths).encode()

    for source in (CANONICAL_ROOT / "skills").rglob("*"):
        if not source.is_file():
            continue
        if source.name == "SKILL.md":
            validate_skill(source)
        relative = source.relative_to(CANONICAL_ROOT / "skills")
        content = source.read_bytes()
        expected[CLAUDE_ROOT / "skills" / relative] = content
        expected[CURSOR_ROOT / "skills" / relative] = content
    return expected


def managed_files() -> set[Path]:
    files = {ROOT / "CLAUDE.md"}
    files.update((CLAUDE_ROOT / "rules").glob("*.md"))
    files.update((CURSOR_ROOT / "rules").glob("*.mdc"))
    for root in (CLAUDE_ROOT / "skills", CURSOR_ROOT / "skills"):
        files.update(path for path in root.rglob("*") if path.is_file())
    return files


def sync(expected: dict[Path, bytes]) -> None:
    for path in managed_files() - set(expected):
        path.unlink()
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    for root in (CLAUDE_ROOT / "skills", CURSOR_ROOT / "skills"):
        for directory in sorted(root.rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()


def check(expected: dict[Path, bytes]) -> list[str]:
    errors = []
    for path in sorted(managed_files() - set(expected)):
        errors.append(f"unexpected generated file: {path.relative_to(ROOT)}")
    for path, content in expected.items():
        if not path.exists():
            errors.append(f"missing generated file: {path.relative_to(ROOT)}")
        elif path.read_bytes() != content:
            errors.append(f"out-of-sync generated file: {path.relative_to(ROOT)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()

    try:
        expected = expected_files()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Agent parity configuration error: {error}", file=sys.stderr)
        return 1

    if args.sync:
        sync(expected)
    errors = check(expected)
    if errors:
        print("Agent guidance is out of sync:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Agent guidance parity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
