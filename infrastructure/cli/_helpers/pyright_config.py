import json
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[3]
BASE_CONFIG = ROOT / "pyproject.toml"
SLOT_CONFIGS = (
    ROOT / "infrastructure/cli/language/pyright.json",
    ROOT / "infrastructure/cli/provider/pyright.json",
)
OUTPUT = ROOT / "pyrightconfig.json"


def base_config() -> dict[str, Any]:
    with BASE_CONFIG.open("rb") as handle:
        pyproject = tomllib.load(handle)
    return cast(dict[str, Any], pyproject["tool"]["pyright"])


def slot_configs() -> list[dict[str, Any]]:
    return [cast(dict[str, Any], json.loads(path.read_text())) for path in SLOT_CONFIGS if path.exists()]


def merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = [*cast(list[Any], merged[key]), *cast(list[Any], value)]
        else:
            merged[key] = value
    return merged


def most_specific_first(environments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(environments, key=lambda environment: len(Path(environment["root"]).parts), reverse=True)


def compose() -> dict[str, Any]:
    config = base_config()
    for slot in slot_configs():
        config = merge(config, slot)
    if "executionEnvironments" in config:
        config["executionEnvironments"] = most_specific_first(config["executionEnvironments"])
    return config


def main() -> None:
    OUTPUT.write_text(json.dumps(compose(), indent=2) + "\n")


if __name__ == "__main__":
    main()
