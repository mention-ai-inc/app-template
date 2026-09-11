from typing import cast

from pydantic import BaseModel, computed_field

from library.domain.value_objects.core import IDValueObject


class PaginatedResponse[ItemT](BaseModel):
    page: list[ItemT]
    has_more: bool

    @computed_field
    @property
    def cursor(self) -> IDValueObject | None:
        if not self.has_more:
            return None

        return max(cast(IDValueObject, getattr(item, "id", "")) for item in self.page) or None
