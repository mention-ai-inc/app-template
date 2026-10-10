from library.domain.audit.classification import by_value_fields, excluded_fields
from tests.domain.audit._widget import Widget


def test_by_value_fields_returns_only_fields_marked_by_value() -> None:
    assert by_value_fields(Widget) == {"status"}


def test_excluded_fields_returns_only_fields_marked_excluded() -> None:
    assert excluded_fields(Widget) == {"secret"}
