import argparse
import shlex
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from mention_template import __version__, agents, templates


def choose(label: str, choices: tuple[str, ...]) -> str:
    while True:
        answer = input(f"{label} ({'/'.join(choices)}): ").strip().lower()
        if answer in choices:
            return answer
        print(f"Choose one of: {', '.join(choices)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a project and continue setup in Claude Code or Codex.")
    parser.add_argument("--version", action="version", version=f"mention-template {__version__}")
    parser.add_argument("--agent", choices=agents.AGENTS)
    parser.add_argument("--cloud", choices=templates.CLOUDS)
    parser.add_argument("--directory", type=Path)
    commands = parser.add_subparsers(dest="action")
    resume = commands.add_parser("resume", help="Continue setup in an existing generated repository")
    resume.add_argument("resume_directory", metavar="directory", type=Path, nargs="?", default=Path.cwd())
    resume.add_argument("--agent", choices=agents.AGENTS, default=argparse.SUPPRESS)
    args = parser.parse_args()
    destination: Path | None = None
    try:
        if sys.platform == "win32":
            raise ValueError("Use macOS, Linux, or a WSL terminal. Native Windows is not supported.")
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError("Agent setup requires an interactive terminal. Run mention-template in your terminal.")
        if not shutil.which("git"):
            raise ValueError("Install Git and rerun mention-template before creating a project.")
        if args.action == "resume" and (args.cloud or args.directory):
            raise ValueError("Use resume with a project directory and optional --agent; omit --cloud and --directory.")
        agent = args.agent or choose("Agent", agents.AGENTS)
        command = agents.executable(agent)
        if args.action == "resume":
            destination = Path(args.resume_directory).expanduser().resolve()
        else:
            cloud = args.cloud or choose("Cloud", templates.CLOUDS)
            directory = args.directory
            if directory is None:
                answer = input("New project directory: ").strip()
                if not answer:
                    raise ValueError("A project directory is required")
                directory = Path(answer)
            destination = Path(directory).expanduser().absolute()
            templates.create(cloud, destination)
        agents.validate_project(destination)
        print(
            f"\nResume setup with: mention-template resume {shlex.quote(str(destination))} --agent {agent}", flush=True
        )
        print(f"Opening {agent}. Use its normal sign-in and project trust prompts.\n", flush=True)
        agents.launch(agent, command, destination)
    except (KeyboardInterrupt, EOFError):
        print("\nSetup interrupted. Existing project files have been preserved.", file=sys.stderr)
        return 130
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, subprocess.SubprocessError) as error:
        print(f"Setup error: {error}", file=sys.stderr)
        if destination and (destination / "project.json").exists():
            print(f"Continue with: mention-template resume {shlex.quote(str(destination))}", file=sys.stderr)
        return 1
    return 0
