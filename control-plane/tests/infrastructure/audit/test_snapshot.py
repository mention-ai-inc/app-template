from pydantic import BaseModel, ConfigDict

from control_plane.domain.value_objects.users import OrganizationID
from control_plane.infrastructure.audit.snapshot import (
    flush_snapshot_context,
    init_snapshot_context,
    recall,
    remember,
)


class Widget(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    organization_id: OrganizationID
    status: str


def make_widget(*, status: str = "draft") -> Widget:
    return Widget(organization_id=OrganizationID("org_widget"), status=status)


def test_recall_returns_none_without_an_initialized_context() -> None:
    assert recall(Widget, organization_id=make_widget().organization_id, document_id="w1") is None


def test_remember_then_recall_returns_a_detached_copy() -> None:
    token = init_snapshot_context()
    widget = make_widget()

    remember(widget, document_id="w1")
    recalled = recall(Widget, organization_id=widget.organization_id, document_id="w1")

    assert recalled == widget
    assert recalled is not widget
    flush_snapshot_context(token=token)


def test_remember_keeps_the_first_snapshot_when_called_twice() -> None:
    token = init_snapshot_context()
    widget = make_widget(status="draft")
    remember(widget, document_id="w1")

    widget.status = "published"
    remember(widget, document_id="w1")

    recalled = recall(Widget, organization_id=widget.organization_id, document_id="w1")
    assert recalled is not None
    assert recalled.status == "draft"
    flush_snapshot_context(token=token)


def test_flush_discards_remembered_snapshots() -> None:
    token = init_snapshot_context()
    widget = make_widget()
    remember(widget, document_id="w1")
    flush_snapshot_context(token=token)

    assert recall(Widget, organization_id=widget.organization_id, document_id="w1") is None
