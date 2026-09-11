from typing import ClassVar

import pytest
from pydantic import ConfigDict

from library._testutils.command_dispatcher import FakeCommandDispatcher
from library.domain.commands.base import CommandPayload
from library.domain.value_objects.common import Service
from library.domain.value_objects.users import OrganizationID


class _SampleCommand(CommandPayload):
    SERVICE: ClassVar[Service] = Service.NOTES
    organization_id: OrganizationID
    instruction: str

    model_config = ConfigDict(frozen=True)


def _org() -> OrganizationID:
    return OrganizationID("org_test")


@pytest.fixture(autouse=True)
def _set_service_env(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.setenv("SERVICE", Service.NOTES.value)


async def test_saved_commands_starts_empty() -> None:
    dispatcher = FakeCommandDispatcher()

    assert dispatcher.saved_commands == []


async def test_save_appends_command_with_payload_and_organization() -> None:
    dispatcher = FakeCommandDispatcher()
    payload = _SampleCommand(organization_id=_org(), instruction="do it")

    await dispatcher.save(payload, organization_id=_org())

    assert len(dispatcher.saved_commands) == 1
    saved = dispatcher.saved_commands[0]
    assert saved.payload is payload
    assert saved.organization_id == _org()


async def test_save_records_delay_seconds() -> None:
    dispatcher = FakeCommandDispatcher()
    payload = _SampleCommand(organization_id=_org(), instruction="later")

    await dispatcher.save(payload, organization_id=_org(), delay_seconds=120)

    assert dispatcher.saved_commands[0].delay_seconds == 120


async def test_save_returns_command_id_used_when_provided() -> None:
    dispatcher = FakeCommandDispatcher()
    payload = _SampleCommand(organization_id=_org(), instruction="explicit id")

    returned_id = await dispatcher.save(payload, organization_id=_org())

    assert dispatcher.saved_commands[0].id == returned_id


async def test_quick_save_records_like_save() -> None:
    dispatcher = FakeCommandDispatcher()
    payload = _SampleCommand(organization_id=_org(), instruction="non-transactional")

    returned_id = await dispatcher.quick_save(payload, organization_id=_org(), delay_seconds=30)

    assert len(dispatcher.saved_commands) == 1
    assert dispatcher.saved_commands[0].payload is payload
    assert dispatcher.saved_commands[0].delay_seconds == 30
    assert dispatcher.saved_commands[0].id == returned_id
