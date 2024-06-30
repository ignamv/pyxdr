import pytest
from pyxdr import UnsignedInt, Int, VarOpaque, Struct, FixedOpaque, Enum
from attrs import define


@define
class MyStruct(Struct):
    a: Int.hint
    b: VarOpaque().hint


@define
class WrapperStruct(Struct):
    a: MyStruct


@define
class ParentStruct(Struct):
    a: Int.hint
    b: MyStruct
    c: Int.hint


def test_fixed_opaque():
    assert FixedOpaque(3).pack(b"\x05\x06") == bytes([5, 6, 0, 0])
    with pytest.raises(ValueError):
        FixedOpaque(3).pack(b"\x05\x06\x07\x08")


def test_fixed_opaque_as_member():
    """Check that the options in type hints are respected"""

    @define
    class TmpWrapper(Struct):
        a: FixedOpaque(3).hint

    assert TmpWrapper(a=b"\x05\x06").pack() == bytes([5, 6, 0, 0])


class MyEnum(Enum):
    RED = 1
    BLUE = 4


def test_enum():
    with pytest.raises(ValueError):
        MyEnum.pack(MyEnum(99))
    with pytest.raises(ValueError):
        MyEnum.unpack(bytes([0, 0, 0, 2]))


testcases = [
    (UnsignedInt, bytes([0, 0, 0, 17]), 17),
    (Int, bytes([0, 0, 0, 17]), 17),
    (Int, bytes([0xFF, 0xFF, 0xFF, 0xFE]), -2),
    (VarOpaque(), bytes([0, 0, 0, 3, 5, 6, 7, 0]), b"\x05\x06\x07"),
    (FixedOpaque(3), bytes([5, 6, 7, 0]), b"\x05\x06\x07"),
    (MyEnum, bytes([0, 0, 0, 1]), MyEnum.RED),
    (MyEnum, bytes([0, 0, 0, 4]), MyEnum.BLUE),
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
