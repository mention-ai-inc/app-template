from __future__ import annotations

from admin.common.options import verb


def test_verb_returns_done_when_apply() -> None:
    assert verb(True, done="Rewrote", pending="Would rewrite") == "Rewrote"


def test_verb_returns_pending_when_dry_run() -> None:
    assert verb(False, done="Rewrote", pending="Would rewrite") == "Would rewrite"
