from library.domain.audit.diff import diff_aggregate
from tests.domain.audit._widget import make_widget


def test_diff_captures_by_value_field_with_before_and_after() -> None:
    before = make_widget(status="draft")
    after = make_widget(status="published")

    changes = diff_aggregate(before, after)

    assert len(changes) == 1
    assert changes[0].field == "status"
    assert changes[0].value_captured is True
    assert changes[0].before == "draft"
    assert changes[0].after == "published"


def test_diff_reports_presence_only_for_unmarked_field() -> None:
    before = make_widget(notes="before")
    after = make_widget(notes="after")

    changes = diff_aggregate(before, after)

    assert len(changes) == 1
    assert changes[0].field == "notes"
    assert changes[0].value_captured is False
    assert changes[0].before is None
    assert changes[0].after is None


def test_diff_never_captures_excluded_field() -> None:
    before = make_widget(secret="old-token")
    after = make_widget(secret="new-token")

    changes = diff_aggregate(before, after)

    assert changes == []


def test_diff_returns_empty_when_nothing_changed() -> None:
    widget = make_widget()

    assert diff_aggregate(widget, widget.model_copy(deep=True)) == []
