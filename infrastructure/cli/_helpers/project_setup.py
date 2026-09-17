#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/mention-template/src"))

from mention_template import setup  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(setup.main(Path(__file__).resolve().parents[3]))
