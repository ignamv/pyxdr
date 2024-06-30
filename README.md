# pyxdr: serialize/deserialize using XDR (RFC 1014)

`pyxdr` provides a modern API for serializing and deserializing objects using the External Data Representation from [RFC 1014](https://datatracker.ietf.org/doc/html/rfc1014).

## Installation

```bash
$ pip install pyxdr
```

## Usage

```python
>>> from pyxdr import Int, UnsignedInt, VarOpaque, Struct
```

### Primitive types

Types without options (e.g. Int, UnsignedInt) don't need to be instanced:
`pack` and `unpack` are class methods.
Types with options (e.g. FixedOpaque, which has a length, and VarOpaque, which has an optional maximum length) have to be instanced.

```python
>>> UnsignedInt.pack(4)
b'\x00\x00\x00\x04'
>>> UnsignedInt().pack(4) # Also works
b'\x00\x00\x00\x04'
>>> # unpack returns a tuple with (unpacked value, remaining buffer)
>>> UnsignedInt.unpack(b'\x00\x00\x00\x04')
(4, b'') 
>>> Int.pack(-3)
b'\xff\xff\xff\xfd'
>>> Int.unpack(b'\xff\xff\xff\xfd')
(-3, b'')
>>> VarOpaque().pack(b'pepe')
b'\x00\x00\x00\x04pepe'
>>> VarOpaque().unpack(b'\x00\x00\x00\x04pepe')
(b'pepe', b'')
```

### Structs

`pyxdr` is compatible with bare Python classes, dataclasses, attrs and pydantic.
The only condition is that the attributes use the type hints provided by `pyxdr`, and that the constructor has an argument for each attribute:

```python
>>> class MyClass(Struct):
...     a: UnsignedInt.hint
...     b: VarOpaque().hint
...     def __init__(self, a, b):
...         # If using dataclasses/attrs/pydantic you would omit this
...         self.a = a
...         self.b = b
...
>>> MyClass(a=3, b=b'pepe').pack()
b'\x00\x00\x00\x03\x00\x00\x00\x04pepe'
>>> x, _ = MyClass.unpack(b'\x00\x00\x00\x03\x00\x00\x00\x04pepe')
>>> x.a
3
>>> x.b
b'pepe'
```
The types like `UnsignedInt.hint` are just annotated native python types, so type checking will still work.

You can also nest structs:

```python
>>> from dataclasses import dataclass
>>> @dataclass
... class MyClass(Struct):
...     c: UnsignedInt.hint
...     d: UnsignedInt.hint
...
>>> @dataclass
... class ParentClass(Struct):
...     a: UnsignedInt.hint
...     b: MyClass
...
>>> ParentClass(a=1, b=MyClass(c=3, d=4)).pack()
b'\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x04'
>>> ParentClass.unpack(b'\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x04')
(ParentClass(a=1, b=MyClass(c=3, d=4)), b'')
```
