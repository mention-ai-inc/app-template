import importlib
from typing import Any

migration = importlib.import_module("admin.backfill.migrations.20260911_note_word_count")


class FakeReference:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def update(self, fields: dict[str, Any]) -> None:
        self.data.update(fields)


class FakeDocument:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.reference = FakeReference(data)

    def to_dict(self) -> dict[str, Any]:
        return self.data


class FakeCollection:
    def __init__(self, collection_id: str, documents: list[FakeDocument]) -> None:
        self.id = collection_id
        self.documents = documents

    def stream(self) -> list[FakeDocument]:
        return self.documents


class FakeClient:
    def __init__(self, collections: list[FakeCollection]) -> None:
        self.by_id = {collection.id: collection for collection in collections}

    def collections(self) -> list[FakeCollection]:
        return list(self.by_id.values())

    def collection(self, collection_id: str) -> FakeCollection:
        return self.by_id[collection_id]


def client_with(*documents: dict[str, Any]) -> FakeClient:
    return FakeClient(
        [
            FakeCollection("devnotes_org_1_note", [FakeDocument(document) for document in documents]),
            FakeCollection("devnotes_org_1_events", []),
        ]
    )


def migrate(client: FakeClient, *, apply: bool) -> tuple[int, int]:
    return migration.migrate_organization(db=client, environment="dev", organization_id="org_1", apply=apply)


def test_a_note_without_a_word_count_is_stamped_from_its_body() -> None:
    client = client_with({"title": "Retro", "body": "Start with what went well."})

    assert migrate(client, apply=True) == (1, 0)
    assert client.collection("devnotes_org_1_note").documents[0].data["word_count"] == 5


def test_a_note_that_already_carries_a_word_count_is_left_alone() -> None:
    client = client_with({"title": "Retro", "body": "Start with what went well.", "word_count": 99})

    assert migrate(client, apply=True) == (0, 1)
    assert client.collection("devnotes_org_1_note").documents[0].data["word_count"] == 99


def test_a_dry_run_counts_the_work_without_writing_it() -> None:
    client = client_with({"title": "Retro", "body": "Start with what went well."})

    assert migrate(client, apply=False) == (1, 0)
    assert "word_count" not in client.collection("devnotes_org_1_note").documents[0].data


def test_only_the_note_collections_are_discovered() -> None:
    client = client_with({"title": "Retro", "body": "Start with what went well."})

    assert migration.organization_ids_for(db=client, environment="dev", organization_id=None) == ["org_1"]
    assert migration.organization_ids_for(db=client, environment="dev", organization_id="org_2") == ["org_2"]
