from dataclasses import dataclass, field
from typing import Any, Literal

BatchOperation = tuple[str, tuple[Any, ...], dict[str, Any]]
MAX_BATCH_OPERATIONS = 100


@dataclass
class BufferedWrite:
    container_name: str
    cosmos_id: str
    partition_value: str
    operation: Literal["upsert", "delete", "patch"]
    item: dict[str, Any] | None
    patch_operations: list[dict[str, Any]] | None
    etag: str | None

    def to_batch_operation(self) -> BatchOperation:
        conditions: dict[str, Any] = {} if self.etag is None else {"if_match_etag": self.etag}
        if self.operation == "delete":
            return ("delete", (self.cosmos_id,), conditions)
        if self.operation == "patch":
            return ("patch", (self.cosmos_id, self.patch_operations or []), conditions)
        return ("upsert", (self.item or {},), conditions)


@dataclass
class CosmosTransaction:
    writes: list[BufferedWrite] = field(default_factory=list[BufferedWrite])
    read_etags: dict[tuple[str, str], str | None] = field(default_factory=dict[tuple[str, str], str | None])
    has_written: bool = False

    def collapsed_writes(self) -> list[BufferedWrite]:
        positions: dict[str, int] = {}
        collapsed: list[BufferedWrite] = []
        for buffered in self.writes:
            position = positions.get(buffered.cosmos_id)
            if position is None:
                positions[buffered.cosmos_id] = len(collapsed)
                collapsed.append(buffered)
            else:
                collapsed[position] = buffered
        return collapsed

    def logical_partitions(self) -> set[tuple[str, str]]:
        return {(buffered.container_name, buffered.partition_value) for buffered in self.writes}
