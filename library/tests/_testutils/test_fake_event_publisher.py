from library._testutils.event_publisher import FakeEventPublisher
from library.domain.events.base import EventPayload
from library.domain.value_objects.users import OrganizationID


class _SampleEvent(EventPayload):
    organization_id: OrganizationID
    note: str


def _org() -> OrganizationID:
    return OrganizationID("org_test")


async def test_saved_events_starts_empty() -> None:
    publisher = FakeEventPublisher()

    assert publisher.saved_events == []


async def test_save_appends_event_with_payload_and_organization() -> None:
    publisher = FakeEventPublisher()
    payload = _SampleEvent(organization_id=_org(), note="something happened")

    await publisher.save(payload, organization_id=_org())

    assert len(publisher.saved_events) == 1
    saved = publisher.saved_events[0]
    assert saved.payload is payload
    assert saved.organization_id == _org()


async def test_save_returns_event_id_used() -> None:
    publisher = FakeEventPublisher()
    payload = _SampleEvent(organization_id=_org(), note="x")

    returned_id = await publisher.save(payload, organization_id=_org())

    assert publisher.saved_events[0].id == returned_id


async def test_quick_save_records_like_save() -> None:
    publisher = FakeEventPublisher()
    payload = _SampleEvent(organization_id=_org(), note="non-transactional")

    returned_id = await publisher.quick_save(payload, organization_id=_org())

    assert len(publisher.saved_events) == 1
    assert publisher.saved_events[0].payload is payload
    assert publisher.saved_events[0].id == returned_id
