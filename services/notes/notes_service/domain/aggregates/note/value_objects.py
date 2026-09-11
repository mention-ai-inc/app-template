from library.domain.value_objects.core import EnumValueObject, StringValueObject


class NoteTitle(StringValueObject):
    pass


class NoteBody(StringValueObject):
    pass


class NoteSummary(StringValueObject):
    pass


class NoteStatus(EnumValueObject):
    PENDING = "pending"
    SUMMARIZING = "summarizing"
    SUMMARIZED = "summarized"
