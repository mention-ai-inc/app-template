import os
import shutil
from pathlib import Path

from mention_template import setup

AGENTS = ("claude", "codex")
INSTALLATION = {
    "claude": "https://code.claude.com/docs/en/setup",
    "codex": "https://developers.openai.com/codex/cli",
}


def executable(agent: str) -> str:
    command = shutil.which(agent)
    if not command:
        raise ValueError(
            f"{agent} is not installed or is not on PATH. Install and sign in using {INSTALLATION[agent]}, then rerun."
        )
    return command


def validate_project(root: Path) -> None:
    setup.configuration(root)
    state = setup.load(root / setup.STATE)
    if not isinstance(state.get("files"), dict) or not isinstance(state.get("rendered"), dict):
        raise ValueError("Project setup state is invalid; restore .project-template.json before resuming")
    for relative in (
        "infrastructure/cli/_bin/m",
        ".agents/skills/start-project/SKILL.md",
        ".claude/skills/start-project/SKILL.md",
    ):
        if not (root / relative).is_file():
            raise ValueError(f"This project is missing {relative}. Restore it from the original template revision.")
    if Path(setup.run(root, "git", "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise ValueError("Resume from the generated project's repository root")


def arguments(agent: str, command: str) -> list[str]:
    skill = ".claude/skills/start-project/SKILL.md" if agent == "claude" else ".agents/skills/start-project/SKILL.md"
    prompt = (
        f"Read AGENTS.md and {skill}, then guide me through setup in this existing generated project. "
        "Inspect project.json, .project-template.json, and the appropriate doctor stage before asking questions. "
        "Do not create another repository or repeat completed setup. Use the checked-in infrastructure/cli/_bin/m "
        "when m is not on PATH. Help me reach the signed-in notes demo with a generated summary. "
        "Project creation does not authorize publication, cloud provisioning, deployment, or deletion; "
        "present the concrete next action and obtain my request before doing those things. "
        "Keep secrets out of the conversation and committed files."
    )
    return [command, prompt]


def launch(agent: str, command: str, root: Path) -> None:
    os.chdir(root)
    os.execv(command, arguments(agent, command))
