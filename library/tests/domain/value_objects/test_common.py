import pytest
from pydantic import BaseModel

from library.domain.errors import DomainError
from library.domain.value_objects.common import EntitySet, PresignedURL


class _Widget(BaseModel):
    name: str


def test_presigned_url_accepts_any_providers_signed_url() -> None:
    google = PresignedURL("https://storage.googleapis.com/bucket/object?X-Goog-Signature=abc")
    amazon = PresignedURL("https://bucket.s3.amazonaws.com/object?X-Amz-Signature=abc")
    azure = PresignedURL("https://account.blob.core.windows.net/container/object?sig=abc")

    assert google.startswith("https://")
    assert amazon.startswith("https://")
    assert azure.startswith("https://")


def test_presigned_url_rejects_a_url_that_is_not_absolute_https() -> None:
    with pytest.raises(DomainError):
        PresignedURL("http://storage.googleapis.com/bucket/object")

    with pytest.raises(DomainError):
        PresignedURL("/bucket/object")


def test_entity_set_raises_a_domain_error_for_a_missing_key() -> None:
    entities = EntitySet[str, _Widget]({"a": _Widget(name="a")})

    assert entities["a"].name == "a"
    with pytest.raises(DomainError):
        entities["missing"]
