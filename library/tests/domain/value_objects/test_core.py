import re
import uuid

import pytest

from library.domain.value_objects.core import IDValueObject, ModelValueObject


class _PrefixedId(IDValueObject):
    PREFIX = "tst_"


class _Unprefixed(IDValueObject):
    PREFIX = ""


class _SimpleMVO(ModelValueObject):
    org: str
    user: str


class _NumericMVO(ModelValueObject):
    org: str
    count: int


class _NestedMVO(ModelValueObject):
    a: str
    inner: _SimpleMVO


def test_id_with_no_argument_generates_id_with_prefix() -> None:
    generated = _PrefixedId()

    assert generated.startswith("tst_")
    assert len(generated) > len("tst_")


def test_id_with_no_argument_produces_distinct_values() -> None:
    a = _PrefixedId()
    b = _PrefixedId()

    assert a != b


def test_id_from_uuid_object_embeds_that_uuid() -> None:
    raw = uuid.UUID("12345678-1234-1234-1234-123456789abc")

    generated = _PrefixedId(raw)

    assert generated == f"tst_{raw.hex}"


def test_id_with_correct_prefix_is_preserved() -> None:
    generated = _PrefixedId("tst_already_prefixed")

    assert generated == "tst_already_prefixed"


def test_id_without_prefix_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid ID"):
        _PrefixedId("no_prefix_here")


def test_id_construction_is_idempotent() -> None:
    once = _PrefixedId("tst_abc123")
    twice = _PrefixedId(once)

    assert once == twice
    assert str(twice) == "tst_abc123"


def test_id_from_json_is_deterministic() -> None:
    a = _PrefixedId.from_json("the same input")
    b = _PrefixedId.from_json("the same input")

    assert a == b


def test_id_from_json_different_inputs_produce_different_ids() -> None:
    a = _PrefixedId.from_json("input one")
    b = _PrefixedId.from_json("input two")

    assert a != b


def test_id_from_json_includes_prefix() -> None:
    generated = _PrefixedId.from_json("anything")

    assert generated.startswith("tst_")


def test_id_with_empty_prefix_accepts_any_string() -> None:
    generated = _Unprefixed("anything-goes")

    assert generated == "anything-goes"


def test_to_id_produces_url_safe_output() -> None:
    mvo = _SimpleMVO(org="acme", user="alice")

    encoded = mvo.to_id()

    assert re.fullmatch(r"[A-Za-z0-9_=-]+", encoded)


def test_simple_round_trip() -> None:
    original = _SimpleMVO(org="acme", user="alice")

    assert _SimpleMVO.from_id(id=original.to_id()) == original


def test_numeric_field_round_trip_preserves_int_type() -> None:
    original = _NumericMVO(org="acme", count=42)

    restored = _NumericMVO.from_id(id=original.to_id())

    assert restored == original
    assert isinstance(restored.count, int)


def test_nested_mvo_round_trip() -> None:
    original = _NestedMVO(a="outer", inner=_SimpleMVO(org="acme", user="alice"))

    assert _NestedMVO.from_id(id=original.to_id()) == original


def test_round_trip_survives_hyphens_in_field_values() -> None:
    original = _SimpleMVO(org="ac-me", user="al-ice")

    assert _SimpleMVO.from_id(id=original.to_id()) == original


def test_round_trip_survives_special_characters() -> None:
    original = _SimpleMVO(org='quotes "and" slashes/and\\backslashes', user="emoji 🎉 unicode café")

    assert _SimpleMVO.from_id(id=original.to_id()) == original


def test_round_trip_survives_empty_string_field() -> None:
    original = _SimpleMVO(org="", user="alice")

    assert _SimpleMVO.from_id(id=original.to_id()) == original


def test_distinct_values_produce_distinct_ids() -> None:
    a = _SimpleMVO(org="acme", user="alice").to_id()
    b = _SimpleMVO(org="acme", user="bob").to_id()

    assert a != b


def test_equal_values_produce_equal_ids() -> None:
    a = _SimpleMVO(org="acme", user="alice").to_id()
    b = _SimpleMVO(org="acme", user="alice").to_id()

    assert a == b
