from contextlib import AbstractAsyncContextManager

from library.application.ports.transactions import ITransaction
from library.providers.registry import get_cloud_provider


def unit_of_work() -> AbstractAsyncContextManager[None]:
    return get_cloud_provider().unit_of_work()


def get_current_uow() -> ITransaction:
    return get_cloud_provider().current_transaction()
