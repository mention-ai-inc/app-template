from typing import Any

from library.application.ports.documents import IDocumentStore
from tests.infrastructure.persistence.mocks import MainEntity, MockPartitionKey, SimpleEntity

type SimpleStore = IDocumentStore[SimpleEntity, MockPartitionKey, Any]
type MainStore = IDocumentStore[MainEntity, MockPartitionKey, Any]
