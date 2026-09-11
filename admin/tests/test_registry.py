from __future__ import annotations

import pytest

from admin.backfill.registry import Backfill, discover, get


def test_discover_returns_backfill_instances() -> None:
    assert discover()
    assert all(isinstance(backfill, Backfill) for backfill in discover())


def test_get_returns_named_backfill() -> None:
    assert get("note-word-count").name == "note-word-count"


def test_get_raises_on_unknown_name() -> None:
    with pytest.raises(SystemExit):
        get("does-not-exist")
