import pytest
from pyxdr import UnsignedInt, Int, Opaque, Struct
from attrs import define


@define
class MyStruct(Struct):
    a: Int.hint
    b: Opaque.hint


@define
class WrapperStruct(Struct):
    a: MyStruct


@define
class ParentStruct(Struct):
    a: Int.hint
    b: MyStruct
    c: Int.hint


testcases = [
    (UnsignedInt, bytes([0, 0, 0, 17]), 17),
    (Int, bytes([0, 0, 0, 17]), 17),
    (Int, bytes([0xFF, 0xFF, 0xFF, 0xFE]), -2),
    (Opaque, bytes([0, 0, 0, 3, 5, 6, 7, 0]), b"\x05\x06\x07"),
    (
        MyStruct,
        bytes([0xFF, 0xFF, 0xFF, 0xFD, 0, 0, 0, 1, 0xEA, 0, 0, 0]),
        MyStruct(a=-3, b=b"\xea"),
    ),
    (
        WrapperStruct,
        bytes([0xFF, 0xFF, 0xFF, 0xFD, 0, 0, 0, 1, 0xEA, 0, 0, 0]),
        WrapperStruct(a=MyStruct(a=-3, b=b"\xea")),
    ),
    (
        ParentStruct,
        bytes(
            [0, 0, 0, 8, 0xFF, 0xFF, 0xFF, 0xFD, 0, 0, 0, 1, 0xEA, 0, 0, 0, 0, 0, 0, 5]
        ),
        ParentStruct(a=8, b=MyStruct(a=-3, b=b"\xea"), c=5),
    ),
]


@pytest.mark.parametrize("cls,packed,unpacked", testcases)
def test_pack(cls, packed, unpacked):
    assert cls.pack(unpacked) == packed


@pytest.mark.parametrize("cls,packed,unpacked", testcases)
def test_unpack(cls, packed, unpacked):
    actual_unpacked, rest = cls.unpack(packed)
    assert actual_unpacked == unpacked
    assert not rest
