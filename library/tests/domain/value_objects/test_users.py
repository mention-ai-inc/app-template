import pytest

from library.domain.errors import DomainError
from library.domain.value_objects.users import OrganizationID, OrganizationPublicMetadata, UserID, UserPublicMetadata


def test_user_id_requires_the_clerk_prefix() -> None:
    assert UserID("user_1") == "user_1"
    with pytest.raises(DomainError):
        UserID("1")


def test_organization_id_requires_the_clerk_prefix() -> None:
    assert OrganizationID("org_1") == "org_1"
    with pytest.raises(DomainError):
        OrganizationID("1")


def test_organization_public_metadata_drops_none_values() -> None:
    assert OrganizationPublicMetadata.model_validate({"anything": None}) == OrganizationPublicMetadata()


def test_user_public_metadata_treats_none_as_empty() -> None:
    assert UserPublicMetadata.model_validate(None) == UserPublicMetadata()
