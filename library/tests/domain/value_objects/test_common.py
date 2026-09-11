import pytest
from pydantic import BaseModel

from library.domain.errors import DomainError
from library.domain.value_objects.common import EntitySet, PresignedURL


class _Widget(BaseModel):
    name: str


def test_presigned_url_accepts_a_google_cloud_storage_url() -> None:
    url = PresignedURL("https://storage.googleapis.com/bucket/object?X-Goog-Signature=abc")

    assert url.startswith("https://storage.googleapis.com/")


def test_presigned_url_rejects_other_hosts() -> None:
    with pytest.raises(DomainError):
        PresignedURL("https://example.com/bucket/object")


def test_entity_set_raises_a_domain_error_for_a_missing_key() -> None:
    entities = EntitySet[str, _Widget]({"a": _Widget(name="a")})

    assert entities["a"].name == "a"
    with pytest.raises(DomainError):
        entities["missing"]
