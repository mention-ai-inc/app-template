#!/usr/bin/env python3
from pathlib import Path

from mention_template import setup

if __name__ == "__main__":
    raise SystemExit(setup.main(Path(__file__).resolve().parents[3]))
