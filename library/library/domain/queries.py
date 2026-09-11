from typing import Self

from pydantic import BaseModel, model_validator


class Pagination[IDT: str | int](BaseModel):
    cursor: IDT | None
    page_size: int


class PaginatedQueryResults[ItemT, IDT: str | int](BaseModel):
    page: list[ItemT]
    next_cursor: IDT | None
    has_more: bool

    @model_validator(mode="after")
    def remove_cursor_if_not_has_more(self) -> Self:
        if not self.has_more:
            self.next_cursor = None
        return self
