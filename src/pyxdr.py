from abc import ABC, abstractmethod
import struct
import typing
import enum


class Serializable(ABC):
    @abstractmethod
    def pack(self, value) -> bytes:
        pass

    @abstractmethod
    def unpack(self, value: bytes):
        pass


class XDRPrimitive(Serializable):
    @classmethod
    def pack(cls, value) -> bytes:
        return struct.pack(cls.format_, value)

    @classmethod
    def unpack(cls, packed: bytes):
        size = struct.calcsize(cls.format_)
        (unpacked,) = struct.unpack_from(cls.format_, packed)
        return unpacked, packed[size:]


def native_type(native):
    def inner(cls):
        cls.hint = typing.Annotated[native, cls]
        return cls

    return inner


class FixedOpaque(XDRPrimitive):
    """Fixed-length opaque data"""

    def __init__(self, length):
        self.length = length
        self.padded_length = length + (-length) % 4

    @property
    def hint(self):
        return typing.Annotated[bytes, self]

    def pack(self, value: bytes) -> bytes:
        if len(value) > self.length:
            raise ValueError(
                f"Tried to pack value with length {len(value)} in Opaque of length {self.length}"
            )
        padding = b"\x00" * (self.padded_length - len(value))
        return value + padding

    def unpack(self, packed: bytes) -> bytes:
        value, packed = packed[: self.length], packed[self.padded_length :]
        return value, packed


@native_type(bytes)
class VarOpaque(XDRPrimitive):
    """Variable-length opaque data"""

    # TODO: implement maximum length

    @classmethod
    def pack(self, value: bytes) -> bytes:
        padding = b"\x00" * (-len(value) % 4)
        return UnsignedInt.pack(len(value)) + value + padding

    @classmethod
    def unpack(self, packed: bytes) -> bytes:
        length, packed = UnsignedInt.unpack(packed)
        padded_length = length + (-length) % 4
        value, packed = packed[:length], packed[padded_length:]
        return value, packed


@native_type(int)
class UnsignedInt(XDRPrimitive):
    format_ = ">I"


@native_type(int)
class Int(XDRPrimitive):
    format_ = ">i"


def _get_serializer_from_type(type_):
    if typing.get_origin(type_) is typing.Annotated:
        # The annotation might be a class (for types without options e.g. Int)
        # or an instance (for types with options e.g. FixedOpaque)
        (serializer,) = [
            x
            for x in typing.get_args(type_)
            if isinstance(x, Serializable) or issubclass(x, Serializable)
        ]
    else:
        assert issubclass(type_, Serializable)
        serializer = type_
    return serializer


class Struct(Serializable):
    def deletme__init__(self, **kwargs):
        required = set(self.__annotations__) - set(dir(type(self)))
        missing = required - set(kwargs)
        if missing:
            raise ValueError("Missing arguments: " + ", ".join(missing))
        unrecognized = set(kwargs) - set(self.__annotations__)
        if unrecognized:
            raise ValueError("Unrecognized arguments: " + ", ".join(unrecognized))
        for name, type_ in self.__annotations__.items():
            try:
                value = kwargs[name]
            except KeyError:
                # Argument not specified, do we have a default value?
                try:
                    value = getattr(type(self), name)
                except AttributeError:
                    raise ValueError(f"Missing argument {name}")
            if not isinstance(value, type_):
                value = type_(value)
            setattr(self, name, value)

    def pack(self) -> bytes:
        pieces = []
        for name, type_ in typing.get_type_hints(self, include_extras=True).items():
            pieces.append(_get_serializer_from_type(type_).pack(getattr(self, name)))
        return b"".join(pieces)

    @classmethod
    def unpack(cls, packed: bytes):
        kwargs = {}
        for name, type_ in typing.get_type_hints(cls, include_extras=True).items():
            kwargs[name], packed = _get_serializer_from_type(type_).unpack(packed)
        return cls(**kwargs), packed


class Enum(enum.Enum):
    @classmethod
    def _assert_valid(cls, value):
        if value not in cls:
            raise ValueError(f"Invalid value {value} for {cls}")

    def pack(self) -> bytes:
        return UnsignedInt.pack(self.value)

    @classmethod
    def unpack(cls, buffer: bytes):
        value, buffer = UnsignedInt.unpack(buffer)
        return cls(value), buffer
