#!/usr/bin/env python3


from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PRD_ROOT = ROOT / "docs" / "product" / "prds"
DOCS_ROOT = ROOT / "docs"

FORWARD_FIELDS = ("Depends on", "Changes", "Supersedes")
DERIVED_FIELDS = ("Depended on by", "Changed by", "Superseded by")
INVERSE = {"Depends on": "Depended on by", "Changes": "Changed by", "Supersedes": "Superseded by"}
FIELD_ORDER = ("Status", "Depends on", "Depended on by", "Changes", "Changed by", "Supersedes", "Superseded by")
ALWAYS_PRESENT = ("Status", "Depends on", "Depended on by")
ALLOWED_STATUSES = ("Draft", "Reviewed", "Reviewed, deliberately out of v1")

TITLE_PATTERN = re.compile(r"^# PRD (\d{2}): (.+)$")
FIELD_PATTERN = re.compile(r"^\*\*([A-Za-z ]+):\*\* (.*)$")
REFERENCE_PATTERN = re.compile(r"PRD (\d{2})(?:\s*\([^)]*\))?((?:\s*§\d+(?:-\d+)?(?:\s*,\s*§\d+(?:-\d+)?)*)?)")
SECTION_PATTERN = re.compile(r"^§(\d+)(?:-(\d+))?$")
REQUIREMENT_PATTERN = re.compile(r"^(\d+)\. ")
DECISION_PATTERN = re.compile(r"^- \*\*(\d{4}-\d{2}-\d{2}) — PRD (\d{2})")
ANY_PRD_PATTERN = re.compile(r"PRD (\d{2})\b")
BANNED_NOTATIONS = (
    (re.compile(r"^## (?:Amended|Superseded|Supersedes|Amends)\b"), "an amendment section"),
    (re.compile(r"^\*\*Amended by PRD \d{2}"), "a bold inline amendment paragraph"),
    (re.compile(r"(?:Amended|Superseded) on \d{4}-\d{2}-\d{2}"), "a dated inline amendment note"),
)


@dataclass
class Reference:
    number: str
    sections: list[tuple[int, int]] = field(default_factory=list)

    def render(self, titles: dict[str, str]) -> str:
        name = titles.get(self.number, "unknown")
        if not self.sections:
            return f"PRD {self.number} ({name})"
        spans = ", ".join(f"§{low}" if low == high else f"§{low}-{high}" for low, high in self.sections)
        return f"PRD {self.number} ({name}) {spans}"


@dataclass
class Document:
    path: Path
    number: str
    title: str
    lines: list[str]
    header_start: int
    header_end: int
    fields: dict[str, str]
    references: dict[str, list[Reference]]
    requirements: set[int]
    decisions: set[str]


def parse(path: Path) -> tuple[Document | None, list[str]]:
    problems: list[str] = []
    lines = path.read_text().splitlines()
    if not lines:
        return None, [f"{path.name}: file is empty"]
    title_match = TITLE_PATTERN.match(lines[0])
    if title_match is None:
        return None, [f"{path.name}:1: first line must read '# PRD NN: Title'"]
    number, title = title_match.group(1), title_match.group(2)
    if not path.name.startswith(f"{number}-"):
        problems.append(f"{path.name}:1: title says PRD {number} but the filename says otherwise")

    header_start = None
    header_end = None
    fields: dict[str, str] = {}
    order: list[str] = []
    for index, line in enumerate(lines):
        match = FIELD_PATTERN.match(line)
        if match is None:
            if header_start is not None and line.strip() == "":
                break
            continue
        if header_start is None:
            header_start = index
        header_end = index
        name, value = match.group(1), match.group(2).strip()
        if name in fields:
            problems.append(f"{path.name}:{index + 1}: duplicate field '{name}'")
        fields[name] = value
        order.append(name)
    if header_start is None or header_end is None:
        return None, [*problems, f"{path.name}: no header block found"]

    for name in order:
        if name not in FIELD_ORDER:
            problems.append(f"{path.name}: unknown header field '{name}'")
    known = [name for name in order if name in FIELD_ORDER]
    if known != sorted(known, key=FIELD_ORDER.index):
        expected = ", ".join(name for name in FIELD_ORDER if name in known)
        problems.append(f"{path.name}: header fields out of order; expected {expected}")

    references: dict[str, list[Reference]] = {}
    for name in (*FORWARD_FIELDS, *DERIVED_FIELDS):
        value = fields.get(name)
        references[name] = [] if value is None else read_references(value, path=path, name=name, problems=problems)

    return (
        Document(
            path=path,
            number=number,
            title=title,
            lines=lines,
            header_start=header_start,
            header_end=header_end,
            fields=fields,
            references=references,
            requirements=read_requirements(lines),
            decisions=read_decisions(lines),
        ),
        problems,
    )


def read_references(value: str, *, path: Path, name: str, problems: list[str]) -> list[Reference]:
    if value == "none":
        return []
    references: list[Reference] = []
    for match in REFERENCE_PATTERN.finditer(value):
        sections: list[tuple[int, int]] = []
        for piece in match.group(2).split(","):
            piece = piece.strip()
            if not piece:
                continue
            span = SECTION_PATTERN.match(piece)
            if span is None:
                problems.append(f"{path.name}: cannot read '{piece}' in '{name}'")
                continue
            low = int(span.group(1))
            high = int(span.group(2)) if span.group(2) else low
            if high < low:
                problems.append(f"{path.name}: '{piece}' in '{name}' runs backwards")
            sections.append((low, high))
        references.append(Reference(number=match.group(1), sections=sections))
    if not references:
        problems.append(f"{path.name}: '{name}' names no PRD and is not 'none'")
    return references


def read_requirements(lines: list[str]) -> set[int]:
    numbers: set[int] = set()
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = line.strip() == "## Requirements"
            continue
        if inside:
            match = REQUIREMENT_PATTERN.match(line)
            if match is not None:
                numbers.add(int(match.group(1)))
    return numbers


def read_decisions(lines: list[str]) -> set[str]:
    numbers: set[str] = set()
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = line.strip() == "## Decision log"
            continue
        if inside:
            match = DECISION_PATTERN.match(line)
            if match is not None:
                numbers.add(match.group(2))
    return numbers


def derive(documents: dict[str, Document]) -> dict[str, dict[str, list[Reference]]]:
    derived: dict[str, dict[str, list[Reference]]] = {
        number: {name: [] for name in DERIVED_FIELDS} for number in documents
    }
    for number in sorted(documents):
        document = documents[number]
        for forward in FORWARD_FIELDS:
            for reference in document.references[forward]:
                if reference.number not in derived:
                    continue
                derived[reference.number][INVERSE[forward]].append(
                    Reference(number=number, sections=list(reference.sections))
                )
    return derived


def render(references: list[Reference], titles: dict[str, str]) -> str:
    if not references:
        return "none"
    return ", ".join(reference.render(titles) for reference in sorted(references, key=lambda item: item.number))


def check(documents: dict[str, Document], titles: dict[str, str]) -> list[str]:
    problems: list[str] = []
    derived = derive(documents)
    for number in sorted(documents):
        document = documents[number]
        name = document.path.name

        status = document.fields.get("Status")
        if status not in ALLOWED_STATUSES:
            allowed = " | ".join(ALLOWED_STATUSES)
            problems.append(f"{name}: Status is '{status}'; must be one of {allowed}")

        for required in ALWAYS_PRESENT:
            if required not in document.fields:
                problems.append(f"{name}: header is missing '{required}'")

        for forward in FORWARD_FIELDS:
            for reference in document.references[forward]:
                if reference.number not in documents:
                    problems.append(f"{name}: '{forward}' names PRD {reference.number}, which does not exist")
                    continue
                if reference.number == number:
                    problems.append(f"{name}: '{forward}' names itself")
                target = documents[reference.number]
                for low, high in reference.sections:
                    missing = [value for value in range(low, high + 1) if value not in target.requirements]
                    if missing:
                        spans = ", ".join(str(value) for value in missing)
                        problems.append(
                            f"{name}: '{forward}' names PRD {reference.number} §{spans}, "
                            f"which PRD {reference.number} has no requirement for"
                        )

        for derived_field in DERIVED_FIELDS:
            expected = render(derived[number][derived_field], titles)
            present = document.fields.get(derived_field, "none")
            if expected == "none" and derived_field not in document.fields:
                continue
            if present != expected:
                problems.append(
                    f"{name}: '{derived_field}' reads '{present}' but the graph says '{expected}'; run m sync-prd-links"
                )

        changed_by = {reference.number for reference in derived[number]["Changed by"]}
        superseded_by = {reference.number for reference in derived[number]["Superseded by"]}
        for source in sorted(changed_by | superseded_by):
            if source not in document.decisions:
                problems.append(
                    f"{name}: PRD {source} changes this PRD but the Decision log has no entry naming PRD {source}"
                )
    return problems


def check_readme(documents: dict[str, Document]) -> list[str]:
    path = PRD_ROOT / "README.md"
    rows = readme_rows(documents)
    present = [line for line in path.read_text().splitlines() if re.match(r"^\| \d{2} \|", line)]
    if present == rows:
        return []
    return ["README.md: the index table is out of date; run m sync-prd-links"]


def readme_rows(documents: dict[str, Document]) -> list[str]:
    path = PRD_ROOT / "README.md"
    groups: dict[str, str] = {}
    for line in path.read_text().splitlines():
        match = re.match(r"^\| (\d{2}) \| .* \| (.+?) \| .* \|$", line)
        if match is not None:
            groups[match.group(1)] = match.group(2)
    rows: list[str] = []
    for number in sorted(documents):
        document = documents[number]
        group = groups.get(number, "Ungrouped")
        rows.append(f"| {number} | {document.title} | {group} | {document.fields.get('Status', '')} |")
    return rows


def check_notations(documents: dict[str, Document]) -> list[str]:
    problems: list[str] = []
    for number in sorted(documents):
        document = documents[number]
        inside_log = False
        for index, line in enumerate(document.lines):
            if line.startswith("## "):
                inside_log = line.strip() == "## Decision log"
            if inside_log:
                continue
            for pattern, description in BANNED_NOTATIONS:
                if pattern.search(line):
                    problems.append(
                        f"{document.path.name}:{index + 1}: {description}; "
                        f"record it in the header fields and the Decision log instead"
                    )
    return problems


def check_references(documents: dict[str, Document]) -> list[str]:
    problems: list[str] = []
    for path in sorted(DOCS_ROOT.rglob("*.md")):
        if path.name == "TEMPLATE.md":
            continue
        for index, line in enumerate(path.read_text().splitlines()):
            for match in ANY_PRD_PATTERN.finditer(line):
                if match.group(1) not in documents:
                    relative = path.relative_to(ROOT)
                    problems.append(f"{relative}:{index + 1}: names PRD {match.group(1)}, which does not exist")
    return problems


def sync(documents: dict[str, Document], titles: dict[str, str]) -> list[str]:
    changed: list[str] = []
    derived = derive(documents)
    for number in sorted(documents):
        document = documents[number]
        lines = list(document.lines)
        block: list[str] = []
        for name in FIELD_ORDER:
            if name in DERIVED_FIELDS:
                value = render(derived[number][name], titles)
                if value == "none" and name not in ALWAYS_PRESENT:
                    continue
            elif name in FORWARD_FIELDS:
                if name not in document.fields:
                    continue
                value = render(document.references[name], titles)
                if value == "none" and name not in ALWAYS_PRESENT:
                    continue
            else:
                value = document.fields.get(name, "")
            block.append(f"**{name}:** {value}")
        replaced = lines[: document.header_start] + block + lines[document.header_end + 1 :]
        if replaced != document.lines:
            document.path.write_text("\n".join(replaced) + "\n")
            changed.append(document.path.name)

    path = PRD_ROOT / "README.md"
    rows = readme_rows(documents)
    lines = path.read_text().splitlines()
    rewritten: list[str] = []
    written = False
    for line in lines:
        if re.match(r"^\| \d{2} \|", line):
            if not written:
                rewritten.extend(rows)
                written = True
            continue
        rewritten.append(line)
        if not written and re.match(r"^\|(?:\s*-{3,}\s*\|)+$", line):
            rewritten.extend(rows)
            written = True
    if rewritten != lines:
        path.write_text("\n".join(rewritten) + "\n")
        changed.append(path.name)
    return changed


def load() -> tuple[dict[str, Document], dict[str, str], list[str]]:
    documents: dict[str, Document] = {}
    problems: list[str] = []
    for path in sorted(PRD_ROOT.glob("[0-9][0-9]-*.md")):
        document, found = parse(path)
        problems.extend(found)
        if document is not None:
            documents[document.number] = document
    titles = {number: document.title for number, document in documents.items()}
    return documents, titles, problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or repair the PRD reference graph.")
    parser.add_argument("--sync", action="store_true", help="rewrite derived fields and the README index")
    arguments = parser.parse_args()

    documents, titles, problems = load()

    if arguments.sync:
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            print("\nFix the problems above before syncing.", file=sys.stderr)
            return 1
        changed = sync(documents, titles)
        if changed:
            print(f"Updated {len(changed)} file(s): {', '.join(changed)}")
        else:
            print("PRD links already in sync.")
        return 0

    if not documents:
        print("No PRDs yet; nothing to check.")
        return 0

    problems.extend(check(documents, titles))
    problems.extend(check_readme(documents))
    problems.extend(check_notations(documents))
    problems.extend(check_references(documents))
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print(f"\n{len(problems)} problem(s) in the PRD reference graph.", file=sys.stderr)
        return 1
    print(f"PRD reference graph is consistent across {len(documents)} PRDs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
