from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from pytest_mock import MockerFixture

from library.domain.value_objects.users import OrganizationID, UserRole
from library.infrastructure import users as users_module
from library.infrastructure.errors import InfrastructureError
from library.infrastructure.users import ClerkClient


async def test_make_request_retries_transient_429_then_succeeds(mocker: MockerFixture) -> None:
    fake = __patch_client(mocker, [__response(429), __response(200, body={"data": []})])
    sleep_mock = __patch_sleep(mocker)

    result = await ClerkClient().list_organizations()

    assert result == []
    assert fake.request_count == 2
    assert sleep_mock.await_count == 1


async def test_make_request_raises_after_exhausting_retries(mocker: MockerFixture) -> None:
    fake = __patch_client(mocker, [__response(429), __response(429), __response(429), __response(429)])
    sleep_mock = __patch_sleep(mocker)

    with pytest.raises(InfrastructureError):
        await ClerkClient().list_organizations()

    assert fake.request_count == ClerkClient.RATE_LIMIT_RETRY_ATTEMPTS
    assert sleep_mock.await_count == ClerkClient.RATE_LIMIT_RETRY_ATTEMPTS - 1


async def test_make_request_does_not_retry_non_transient_error(mocker: MockerFixture) -> None:
    fake = __patch_client(mocker, [__response(404, body={"errors": [{"code": "not_found"}]})])
    sleep_mock = __patch_sleep(mocker)

    with pytest.raises(InfrastructureError):
        await ClerkClient().list_organizations()

    assert fake.request_count == 1
    assert sleep_mock.await_count == 0


async def test_make_request_honors_retry_after_header(mocker: MockerFixture) -> None:
    fake = __patch_client(mocker, [__response(429, headers={"Retry-After": "2"}), __response(200, body={"data": []})])
    sleep_mock = __patch_sleep(mocker)

    await ClerkClient().list_organizations()

    assert fake.request_count == 2
    sleep_mock.assert_awaited_once_with(2.0)


async def test_make_request_returns_expected_error_without_retrying(mocker: MockerFixture) -> None:
    fake = __patch_client(mocker, [__response(422, body={"errors": [{"code": "already_a_member_in_organization"}]})])
    sleep_mock = __patch_sleep(mocker)

    await ClerkClient().invite_user_to_organization(
        organization_id=OrganizationID("org_test"), email_address="x@y.com", role=UserRole.MEMBER
    )

    assert fake.request_count == 1
    assert sleep_mock.await_count == 0


async def test_list_organization_member_user_ids_filters_by_role_in_one_request(
    mocker: MockerFixture,
) -> None:
    fake = __patch_client(mocker, [__response(200, body={"data": __memberships()})])

    admin_ids = await ClerkClient().list_organization_member_user_ids(
        organization_id=OrganizationID("org_test"), role=UserRole.ADMIN
    )

    assert admin_ids == ["user_admin"]
    assert fake.request_count == 1


async def test_list_organization_member_user_ids_returns_every_member_without_a_role(
    mocker: MockerFixture,
) -> None:
    __patch_client(mocker, [__response(200, body={"data": __memberships()})])

    user_ids = await ClerkClient().list_organization_member_user_ids(organization_id=OrganizationID("org_test"))

    assert user_ids == ["user_admin", "user_member"]


async def test_list_organization_member_names_reads_the_membership_page_alone(mocker: MockerFixture) -> None:
    fake = __patch_client(
        mocker,
        [
            __response(
                200,
                body={
                    "data": [
                        {"public_user_data": {"user_id": "user_1", "first_name": "Ana", "last_name": "Sokolova"}},
                        {"public_user_data": {"user_id": "user_2", "first_name": "Jonah", "last_name": None}},
                    ]
                },
            )
        ],
    )

    member_names = await ClerkClient().list_organization_member_names(organization_id=OrganizationID("org_test"))

    assert [member.full_name for member in member_names] == ["Ana Sokolova", "Jonah"]
    assert fake.request_count == 1


class _FakeAsyncClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.request_count = 0

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> bool:
        return False

    async def request(self, *_: object, **__: object) -> httpx.Response:
        response = self._responses[self.request_count]
        self.request_count += 1
        return response


def __response(
    status_code: int, *, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=body if body is not None else {"errors": [{"code": "too_many_requests"}]},
        headers=headers or {},
        request=httpx.Request("GET", "https://api.clerk.com/v1/organizations"),
    )


def __patch_client(mocker: MockerFixture, responses: list[httpx.Response]) -> _FakeAsyncClient:
    fake = _FakeAsyncClient(responses)
    mocker.patch.object(users_module.httpx, "AsyncClient", return_value=fake)
    return fake


def __patch_sleep(mocker: MockerFixture) -> AsyncMock:
    return mocker.patch.object(users_module.asyncio, "sleep", new_callable=AsyncMock)


def __memberships() -> list[dict[str, Any]]:
    return [
        {"role": "org:admin", "public_user_data": {"user_id": "user_admin"}},
        {"role": "org:member", "public_user_data": {"user_id": "user_member"}},
    ]
