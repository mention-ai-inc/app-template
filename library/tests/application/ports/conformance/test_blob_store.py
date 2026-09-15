from datetime import UTC, datetime

import pytest

from library.application.ports.blobs import IBlobStore
from library.domain.value_objects.common import PresignedURL
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from tests.application.ports.conformance.providers import ProviderUnderTest

ORGANIZATION_ID = OrganizationID("org_conformance")
FILEPATH = "conformance/one.blob"
OTHER_FILEPATH = "elsewhere/two.blob"


class TestPathConventions:
    def test_the_org_prefix_scopes_by_organization(self, blob_store: IBlobStore) -> None:
        assert blob_store.org_prefix(ORGANIZATION_ID) == f"orgs/{ORGANIZATION_ID}/"

    def test_the_path_to_a_blob_sits_under_the_org_prefix(self, blob_store: IBlobStore) -> None:
        path = blob_store.get_path_to_blob(organization_id=ORGANIZATION_ID, document_id="doc_1", field_id="body")

        assert path == f"{blob_store.org_prefix(ORGANIZATION_ID)}blobs/doc_1/body.blob"

    def test_the_legacy_path_to_a_blob_is_not_scoped_by_organization(self, blob_store: IBlobStore) -> None:
        assert blob_store.get_legacy_path_to_blob(document_id="doc_1", field_id="body") == "blobs/doc_1/body.blob"


class TestContent:
    async def test_a_blob_comes_back_as_it_went_in(self, blob_store: IBlobStore) -> None:
        await blob_store.insert(filepath=FILEPATH, content=b"contents")

        assert await blob_store.get(filepath=FILEPATH) == b"contents"

    async def test_inserting_again_replaces_the_content(self, blob_store: IBlobStore) -> None:
        await blob_store.insert(filepath=FILEPATH, content=b"first")

        await blob_store.insert(filepath=FILEPATH, content=b"second")

        assert await blob_store.get(filepath=FILEPATH) == b"second"

    async def test_exists_reports_whether_the_blob_is_there(self, blob_store: IBlobStore) -> None:
        await blob_store.insert(filepath=FILEPATH, content=b"contents")

        assert await blob_store.exists(filepath=FILEPATH) is True
        assert await blob_store.exists(filepath=OTHER_FILEPATH) is False

    async def test_getting_a_missing_blob_raises(self, blob_store: IBlobStore) -> None:
        with pytest.raises(InfrastructureError) as exc_info:
            await blob_store.get(filepath=FILEPATH)

        assert exc_info.value.error_type == InfrastructureErrorType.CLOUD_ERROR

    async def test_get_saved_at_reports_when_the_blob_landed(self, blob_store: IBlobStore) -> None:
        before = datetime.now(UTC)

        await blob_store.insert(filepath=FILEPATH, content=b"contents")

        saved_at = await blob_store.get_saved_at(filepath=FILEPATH)
        assert saved_at.tzinfo is not None
        assert saved_at >= before

    async def test_get_saved_at_of_a_missing_blob_raises(self, blob_store: IBlobStore) -> None:
        with pytest.raises(InfrastructureError):
            await blob_store.get_saved_at(filepath=FILEPATH)

    async def test_delete_removes_the_blob(self, blob_store: IBlobStore) -> None:
        await blob_store.insert(filepath=FILEPATH, content=b"contents")

        await blob_store.delete(filepath=FILEPATH)

        assert await blob_store.exists(filepath=FILEPATH) is False

    async def test_deleting_a_missing_blob_raises(self, blob_store: IBlobStore) -> None:
        with pytest.raises(InfrastructureError):
            await blob_store.delete(filepath=FILEPATH)


class TestListing:
    async def test_listing_returns_every_blob_by_default(self, blob_store: IBlobStore) -> None:
        await blob_store.insert(filepath=FILEPATH, content=b"one")
        await blob_store.insert(filepath=OTHER_FILEPATH, content=b"two")

        assert sorted(await blob_store.list()) == sorted([FILEPATH, OTHER_FILEPATH])

    async def test_listing_narrows_to_the_prefix(self, blob_store: IBlobStore) -> None:
        await blob_store.insert(filepath=FILEPATH, content=b"one")
        await blob_store.insert(filepath=OTHER_FILEPATH, content=b"two")

        assert await blob_store.list(prefix="conformance/") == [FILEPATH]

    async def test_delete_all_under_removes_only_the_prefix(self, blob_store: IBlobStore) -> None:
        await blob_store.insert(filepath=FILEPATH, content=b"one")
        await blob_store.insert(filepath=OTHER_FILEPATH, content=b"two")

        await blob_store.delete_all_under(prefix="conformance/")

        assert await blob_store.list() == [OTHER_FILEPATH]


class TestPresignedUrls:
    async def test_a_presigned_url_is_an_absolute_https_url(
        self, provider_under_test: ProviderUnderTest, blob_store: IBlobStore
    ) -> None:
        if not provider_under_test.supports_presigned_urls:
            pytest.skip(f"{provider_under_test.name} does not sign blob urls")
        await blob_store.insert(filepath=FILEPATH, content=b"contents")

        url = await blob_store.get_presigned_url(
            filepath=FILEPATH, expiration=600, content_type="application/octet-stream", method="GET"
        )

        assert isinstance(url, PresignedURL)
        assert url.startswith(PresignedURL.REQUIRED_SCHEME)

    async def test_signing_a_missing_blob_creates_it(
        self, provider_under_test: ProviderUnderTest, blob_store: IBlobStore
    ) -> None:
        if not provider_under_test.presigned_urls_create_missing_objects:
            pytest.skip(f"{provider_under_test.name} does not create objects while signing")

        await blob_store.get_presigned_url(
            filepath=FILEPATH, expiration=600, content_type="application/octet-stream", method="PUT"
        )

        assert await blob_store.exists(filepath=FILEPATH) is True
        assert await blob_store.get(filepath=FILEPATH) == b""
