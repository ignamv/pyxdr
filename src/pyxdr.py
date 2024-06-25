from abc import ABC, abstractmethod
import struct
import typing


class Serializable(ABC):
    @abstractmethod
    def pack(self) -> bytes:
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


@native_type(bytes)
class Opaque(XDRPrimitive):
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
        (serializer,) = [
            cls for cls in typing.get_args(type_) if issubclass(cls, Serializable)
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
