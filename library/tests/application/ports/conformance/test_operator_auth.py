import pytest

from library.application.ports.operators import IOperatorAuth
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType


async def test_a_signed_in_operator_comes_back_identified(
    operator_auth: IOperatorAuth, operator_headers: dict[str, str]
) -> None:
    operator = await operator_auth.authenticate(headers=operator_headers)

    assert operator.subject != ""
    assert "@" in operator.email


async def test_the_same_headers_identify_the_same_operator(
    operator_auth: IOperatorAuth, operator_headers: dict[str, str]
) -> None:
    first = await operator_auth.authenticate(headers=operator_headers)
    second = await operator_auth.authenticate(headers=operator_headers)

    assert first == second


async def test_an_unauthenticated_caller_is_refused(operator_auth: IOperatorAuth) -> None:
    with pytest.raises(InfrastructureError) as exc_info:
        await operator_auth.authenticate(headers={})

    assert exc_info.value.error_type == InfrastructureErrorType.OAUTH_ERROR


async def test_the_caller_identity_is_a_non_empty_string(operator_auth: IOperatorAuth) -> None:
    identity = await operator_auth.caller_identity()

    assert isinstance(identity, str)
    assert identity != ""
