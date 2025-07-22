#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import IntEnum
import os
from pathlib import Path
import re
from subprocess import call
import sys
from typing import Any

import aioesphomeapi.api_options_pb2 as pb
import google.protobuf.descriptor_pb2 as descriptor


class WireType(IntEnum):
    """Protocol Buffer wire types as defined in the protobuf spec.

    As specified in the Protocol Buffers encoding guide:
    https://protobuf.dev/programming-guides/encoding/#structure
    """

    VARINT = 0  # int32, int64, uint32, uint64, sint32, sint64, bool, enum
    FIXED64 = 1  # fixed64, sfixed64, double
    LENGTH_DELIMITED = 2  # string, bytes, embedded messages, packed repeated fields
    START_GROUP = 3  # groups (deprecated)
    END_GROUP = 4  # groups (deprecated)
    FIXED32 = 5  # fixed32, sfixed32, float


# Generate with
# protoc --python_out=script/api_protobuf -I esphome/components/api/ api_options.proto


"""Python 3 script to automatically generate C++ classes for ESPHome's native API.

It's pretty crappy spaghetti code, but it works.

you need to install protobuf-compiler:
running protoc --version should return
libprotoc 3.6.1

then run this script with python3 and the files

    esphome/components/api/api_pb2_service.h
    esphome/components/api/api_pb2_service.cpp
    esphome/components/api/api_pb2.h
    esphome/components/api/api_pb2.cpp

will be generated, they still need to be formatted
"""


FILE_HEADER = """// This file was automatically generated with a tool.
// See script/api_protobuf/api_protobuf.py
"""


def indent_list(text: str, padding: str = "  ") -> list[str]:
    """Indent each line of the given text with the specified padding."""
    lines = []
    for line in text.splitlines():
        if line == "":
            p = ""
        elif line.startswith("#ifdef") or line.startswith("#endif"):
            p = ""
        else:
            p = padding
        lines.append(p + line)
    return lines


def indent(text: str, padding: str = "  ") -> str:
    return "\n".join(indent_list(text, padding))


def wrap_with_ifdef(content: str | list[str], ifdef: str | None) -> list[str]:
    """Wrap content with #ifdef directives if ifdef is provided.

    Args:
        content: Single string or list of strings to wrap
        ifdef: The ifdef condition, or None to skip wrapping

    Returns:
        List of strings with ifdef wrapping if needed
    """
    if not ifdef:
        if isinstance(content, str):
            return [content]
        return content

    result = [f"#ifdef {ifdef}"]
    if isinstance(content, str):
        result.append(content)
    else:
        result.extend(content)
    result.append("#endif")
    return result


def camel_to_snake(name: str) -> str:
    # https://stackoverflow.com/a/1176023
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def force_str(force: bool) -> str:
    """Convert a boolean force value to string format for C++ code."""
    return str(force).lower()


class TypeInfo(ABC):
    """Base class for all type information."""

    def __init__(
        self,
        field: descriptor.FieldDescriptorProto,
        needs_decode: bool = True,
        needs_encode: bool = True,
    ) -> None:
        self._field = field
        self._needs_decode = needs_decode
        self._needs_encode = needs_encode

    @property
    def default_value(self) -> str:
        """Get the default value."""
        return ""

    @property
    def name(self) -> str:
        """Get the name of the field."""
        return self._field.name

    @property
    def arg_name(self) -> str:
        """Get the argument name."""
        return self.name

    @property
    def field_name(self) -> str:
        """Get the field name."""
        return self.name

    @property
    def number(self) -> int:
        """Get the field number."""
        return self._field.number

    @property
    def repeated(self) -> bool:
        """Check if the field is repeated."""
        return self._field.label == 3

    @property
    def wire_type(self) -> WireType:
        """Get the wire type for the field."""
        raise NotImplementedError

    @property
    def cpp_type(self) -> str:
        raise NotImplementedError

    @property
    def reference_type(self) -> str:
        return f"{self.cpp_type} "

    @property
    def const_reference_type(self) -> str:
        return f"{self.cpp_type} "

    @property
    def public_content(self) -> str:
        return [self.class_member]

    @property
    def protected_content(self) -> str:
        return []

    @property
    def class_member(self) -> str:
        return f"{self.cpp_type} {self.field_name}{{{self.default_value}}};"

    @property
    def decode_varint_content(self) -> str:
        content = self.decode_varint
        if content is None:
            return None
        return f"case {self.number}: this->{self.field_name} = {content}; break;"

    decode_varint = None

    @property
    def decode_length_content(self) -> str:
        content = self.decode_length
        if content is None:
            return None
        return f"case {self.number}: this->{self.field_name} = {content}; break;"

    decode_length = None

    @property
    def decode_32bit_content(self) -> str:
        content = self.decode_32bit
        if content is None:
            return None
        return f"case {self.number}: this->{self.field_name} = {content}; break;"

    decode_32bit = None

    @property
    def decode_64bit_content(self) -> str:
        content = self.decode_64bit
        if content is None:
            return None
        return f"case {self.number}: this->{self.field_name} = {content}; break;"

    decode_64bit = None

    @property
    def encode_content(self) -> str:
        return f"buffer.{self.encode_func}({self.number}, this->{self.field_name});"

    encode_func = None

    @property
    def dump_content(self) -> str:
        o = f'out.append("  {self.name}: ");\n'
        o += self.dump(f"this->{self.field_name}") + "\n"
        o += 'out.append("\\n");\n'
        return o

    @abstractmethod
    def dump(self, name: str) -> str:
        """Dump the value to the output."""

    def calculate_field_id_size(self) -> int:
        """Calculates the size of a field ID in bytes.

        Returns:
            The number of bytes needed to encode the field ID
        """
        # Calculate the tag by combining field_id and wire_type
        tag = (self.number << 3) | (self.wire_type & 0b111)

        # Calculate the varint size
        if tag < 128:
            return 1  # 7 bits
        if tag < 16384:
            return 2  # 14 bits
        if tag < 2097152:
            return 3  # 21 bits
        if tag < 268435456:
            return 4  # 28 bits
        return 5  # 32 bits (maximum for uint32_t)

    def _get_simple_size_calculation(
        self, name: str, force: bool, base_method: str, value_expr: str = None
    ) -> str:
        """Helper for simple size calculations.

        Args:
            name: Field name
            force: Whether this is for a repeated field
            base_method: Base method name (e.g., "add_int32_field")
            value_expr: Optional value expression (defaults to name)
        """
        field_id_size = self.calculate_field_id_size()
        method = f"{base_method}_repeated" if force else base_method
        value = value_expr if value_expr else name
        return f"ProtoSize::{method}(total_size, {field_id_size}, {value});"

    @abstractmethod
    def get_size_calculation(self, name: str, force: bool = False) -> str:
        """Calculate the size needed for encoding this field.

        Args:
            name: The name of the field
            force: Whether to force encoding the field even if it has a default value
        """

    def get_fixed_size_bytes(self) -> int | None:
        """Get the number of bytes for fixed-size fields (float, double, fixed32, etc).

        Returns:
            The number of bytes (4 or 8) for fixed-size fields, None for variable-size fields.
        """
        return None

    @abstractmethod
    def get_estimated_size(self) -> int:
        """Get estimated size in bytes for this field with typical values.

        Returns:
            Estimated size in bytes including field ID and typical data
        """


TYPE_INFO: dict[int, TypeInfo] = {}

# Unsupported 64-bit types that would add overhead for embedded systems
# TYPE_DOUBLE = 1, TYPE_FIXED64 = 6, TYPE_SFIXED64 = 16, TYPE_SINT64 = 18
UNSUPPORTED_TYPES = {1: "double", 6: "fixed64", 16: "sfixed64", 18: "sint64"}


def validate_field_type(field_type: int, field_name: str = "") -> None:
    """Validate that the field type is supported by ESPHome API.

    Raises ValueError for unsupported 64-bit types.
    """
    if field_type in UNSUPPORTED_TYPES:
        type_name = UNSUPPORTED_TYPES[field_type]
        field_info = f" (field: {field_name})" if field_name else ""
        raise ValueError(
            f"64-bit type '{type_name}'{field_info} is not supported by ESPHome API. "
            "These types add significant overhead for embedded systems. "
            "If you need 64-bit support, please add the necessary encoding/decoding "
            "functions to proto.h/proto.cpp first."
        )


def create_field_type_info(
    field: descriptor.FieldDescriptorProto,
    needs_decode: bool = True,
    needs_encode: bool = True,
) -> TypeInfo:
    """Create the appropriate TypeInfo instance for a field, handling repeated fields and custom options."""
    if field.label == 3:  # repeated
        # Check if this repeated field has fixed_array_size option
        if (fixed_size := get_field_opt(field, pb.fixed_array_size)) is not None:
            return FixedArrayRepeatedType(field, fixed_size)
        return RepeatedTypeInfo(field)

    # Check for fixed_array_size option on bytes fields
    if (
        field.type == 12
        and (fixed_size := get_field_opt(field, pb.fixed_array_size)) is not None
    ):
        return FixedArrayBytesType(field, fixed_size)

    # Special handling for bytes fields
    if field.type == 12:
        return BytesType(field, needs_decode, needs_encode)

    validate_field_type(field.type, field.name)
    return TYPE_INFO[field.type](field)


def register_type(name: int):
    """Decorator to register a type with a name and number."""

    def func(value: TypeInfo) -> TypeInfo:
        """Register the type with the given name and number."""
        TYPE_INFO[name] = value
        return value

    return func


@register_type(1)
class DoubleType(TypeInfo):
    cpp_type = "double"
    default_value = "0.0"
    decode_64bit = "value.as_double()"
    encode_func = "encode_double"
    wire_type = WireType.FIXED64  # Uses wire type 1 according to protobuf spec

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%g", {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        field_id_size = self.calculate_field_id_size()
        return f"ProtoSize::add_double_field(total_size, {field_id_size}, {name});"

    def get_fixed_size_bytes(self) -> int:
        return 8

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 8  # field ID + 8 bytes for double


@register_type(2)
class FloatType(TypeInfo):
    cpp_type = "float"
    default_value = "0.0f"
    decode_32bit = "value.as_float()"
    encode_func = "encode_float"
    wire_type = WireType.FIXED32  # Uses wire type 5

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%g", {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        field_id_size = self.calculate_field_id_size()
        return f"ProtoSize::add_float_field(total_size, {field_id_size}, {name});"

    def get_fixed_size_bytes(self) -> int:
        return 4

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 4  # field ID + 4 bytes for float


@register_type(3)
class Int64Type(TypeInfo):
    cpp_type = "int64_t"
    default_value = "0"
    decode_varint = "value.as_int64()"
    encode_func = "encode_int64"
    wire_type = WireType.VARINT  # Uses wire type 0

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%lld", {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(name, force, "add_int64_field")

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 3  # field ID + 3 bytes typical varint


@register_type(4)
class UInt64Type(TypeInfo):
    cpp_type = "uint64_t"
    default_value = "0"
    decode_varint = "value.as_uint64()"
    encode_func = "encode_uint64"
    wire_type = WireType.VARINT  # Uses wire type 0

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%llu", {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(name, force, "add_uint64_field")

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 3  # field ID + 3 bytes typical varint


@register_type(5)
class Int32Type(TypeInfo):
    cpp_type = "int32_t"
    default_value = "0"
    decode_varint = "value.as_int32()"
    encode_func = "encode_int32"
    wire_type = WireType.VARINT  # Uses wire type 0

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%" PRId32, {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(name, force, "add_int32_field")

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 3  # field ID + 3 bytes typical varint


@register_type(6)
class Fixed64Type(TypeInfo):
    cpp_type = "uint64_t"
    default_value = "0"
    decode_64bit = "value.as_fixed64()"
    encode_func = "encode_fixed64"
    wire_type = WireType.FIXED64  # Uses wire type 1

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%llu", {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        field_id_size = self.calculate_field_id_size()
        return f"ProtoSize::add_fixed64_field(total_size, {field_id_size}, {name});"

    def get_fixed_size_bytes(self) -> int:
        return 8

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 8  # field ID + 8 bytes fixed


@register_type(7)
class Fixed32Type(TypeInfo):
    cpp_type = "uint32_t"
    default_value = "0"
    decode_32bit = "value.as_fixed32()"
    encode_func = "encode_fixed32"
    wire_type = WireType.FIXED32  # Uses wire type 5

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%" PRIu32, {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        field_id_size = self.calculate_field_id_size()
        return f"ProtoSize::add_fixed32_field(total_size, {field_id_size}, {name});"

    def get_fixed_size_bytes(self) -> int:
        return 4

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 4  # field ID + 4 bytes fixed


@register_type(8)
class BoolType(TypeInfo):
    cpp_type = "bool"
    default_value = "false"
    decode_varint = "value.as_bool()"
    encode_func = "encode_bool"
    wire_type = WireType.VARINT  # Uses wire type 0

    def dump(self, name: str) -> str:
        o = f"out.append(YESNO({name}));"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(name, force, "add_bool_field")

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 1  # field ID + 1 byte


@register_type(9)
class StringType(TypeInfo):
    cpp_type = "std::string"
    default_value = ""
    reference_type = "std::string &"
    const_reference_type = "const std::string &"
    decode_length = "value.as_string()"
    encode_func = "encode_string"
    wire_type = WireType.LENGTH_DELIMITED  # Uses wire type 2

    def dump(self, name):
        o = f'out.append("\'").append({name}).append("\'");'
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(name, force, "add_string_field")

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 8  # field ID + 8 bytes typical string


@register_type(11)
class MessageType(TypeInfo):
    @property
    def cpp_type(self) -> str:
        return self._field.type_name[1:]

    default_value = ""
    wire_type = WireType.LENGTH_DELIMITED  # Uses wire type 2

    @property
    def reference_type(self) -> str:
        return f"{self.cpp_type} &"

    @property
    def const_reference_type(self) -> str:
        return f"const {self.cpp_type} &"

    @property
    def encode_func(self) -> str:
        return "encode_message"

    @property
    def decode_length(self) -> str:
        # Override to return None for message types because we can't use template-based
        # decoding when the specific message type isn't known at compile time.
        # Instead, we use the non-template decode_to_message() method which allows
        # runtime polymorphism through virtual function calls.
        return None

    @property
    def decode_length_content(self) -> str:
        # Custom decode that doesn't use templates
        return f"case {self.number}: value.decode_to_message(this->{self.field_name}); break;"

    def dump(self, name: str) -> str:
        o = f"{name}.dump_to(out);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(name, force, "add_message_object")

    def get_estimated_size(self) -> int:
        # For message types, we can't easily estimate the submessage size without
        # access to the actual message definition. This is just a rough estimate.
        return (
            self.calculate_field_id_size() + 16
        )  # field ID + 16 bytes estimated submessage


@register_type(12)
class BytesType(TypeInfo):
    cpp_type = "std::string"
    default_value = ""
    reference_type = "std::string &"
    const_reference_type = "const std::string &"
    encode_func = "encode_bytes"
    decode_length = "value.as_string()"
    wire_type = WireType.LENGTH_DELIMITED  # Uses wire type 2

    @property
    def public_content(self) -> list[str]:
        content: list[str] = []
        # Add std::string storage if message needs decoding
        if self._needs_decode:
            content.append(f"std::string {self.field_name}{{}};")

        if self._needs_encode:
            content.extend(
                [
                    # Add pointer/length fields if message needs encoding
                    f"const uint8_t* {self.field_name}_ptr_{{nullptr}};",
                    f"size_t {self.field_name}_len_{{0}};",
                    # Add setter method if message needs encoding
                    f"void set_{self.field_name}(const uint8_t* data, size_t len) {{",
                    f"  this->{self.field_name}_ptr_ = data;",
                    f"  this->{self.field_name}_len_ = len;",
                    "}",
                ]
            )
        return content

    @property
    def encode_content(self) -> str:
        return f"buffer.encode_bytes({self.number}, this->{self.field_name}_ptr_, this->{self.field_name}_len_);"

    def dump(self, name: str) -> str:
        ptr_dump = f"format_hex_pretty(this->{self.field_name}_ptr_, this->{self.field_name}_len_)"
        str_dump = f"format_hex_pretty(reinterpret_cast<const uint8_t*>(this->{self.field_name}.data()), this->{self.field_name}.size())"

        # For SOURCE_CLIENT only, always use std::string
        if not self._needs_encode:
            return f"out.append({str_dump});"

        # For SOURCE_SERVER, always use pointer/length
        if not self._needs_decode:
            return f"out.append({ptr_dump});"

        # For SOURCE_BOTH, check if pointer is set (sending) or use string (received)
        return (
            f"if (this->{self.field_name}_ptr_ != nullptr) {{\n"
            f"    out.append({ptr_dump});\n"
            f"  }} else {{\n"
            f"    out.append({str_dump});\n"
            f"  }}"
        )

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return f"ProtoSize::add_bytes_field(total_size, {self.calculate_field_id_size()}, this->{self.field_name}_len_);"

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 8  # field ID + 8 bytes typical bytes


class FixedArrayBytesType(TypeInfo):
    """Special type for fixed-size byte arrays."""

    def __init__(self, field: descriptor.FieldDescriptorProto, size: int) -> None:
        super().__init__(field)
        self.array_size = size

    @property
    def cpp_type(self) -> str:
        return "uint8_t"

    @property
    def default_value(self) -> str:
        return "{}"

    @property
    def reference_type(self) -> str:
        return f"uint8_t (&)[{self.array_size}]"

    @property
    def const_reference_type(self) -> str:
        return f"const uint8_t (&)[{self.array_size}]"

    @property
    def public_content(self) -> list[str]:
        # Add both the array and length fields
        return [
            f"uint8_t {self.field_name}[{self.array_size}]{{}};",
            f"uint8_t {self.field_name}_len{{0}};",
        ]

    @property
    def decode_length_content(self) -> str:
        o = f"case {self.number}: {{\n"
        o += "  const std::string &data_str = value.as_string();\n"
        o += f"  this->{self.field_name}_len = data_str.size();\n"
        o += f"  if (this->{self.field_name}_len > {self.array_size}) {{\n"
        o += f"    this->{self.field_name}_len = {self.array_size};\n"
        o += "  }\n"
        o += f"  memcpy(this->{self.field_name}, data_str.data(), this->{self.field_name}_len);\n"
        o += "  break;\n"
        o += "}"
        return o

    @property
    def encode_content(self) -> str:
        return f"buffer.encode_bytes({self.number}, this->{self.field_name}, this->{self.field_name}_len);"

    def dump(self, name: str) -> str:
        o = f"out.append(format_hex_pretty({name}, {name}_len));"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        # Use the actual length stored in the _len field
        length_field = f"this->{self.field_name}_len"
        field_id_size = self.calculate_field_id_size()

        if force:
            # For repeated fields, always calculate size
            return f"total_size += {field_id_size} + ProtoSize::varint(static_cast<uint32_t>({length_field})) + {length_field};"
        else:
            # For non-repeated fields, skip if length is 0 (matching encode_string behavior)
            return (
                f"if ({length_field} != 0) {{\n"
                f"  total_size += {field_id_size} + ProtoSize::varint(static_cast<uint32_t>({length_field})) + {length_field};\n"
                f"}}"
            )

    def get_estimated_size(self) -> int:
        # Estimate based on typical BLE advertisement size
        return (
            self.calculate_field_id_size() + 1 + 31
        )  # field ID + length byte + typical 31 bytes

    @property
    def wire_type(self) -> WireType:
        return WireType.LENGTH_DELIMITED


@register_type(13)
class UInt32Type(TypeInfo):
    cpp_type = "uint32_t"
    default_value = "0"
    decode_varint = "value.as_uint32()"
    encode_func = "encode_uint32"
    wire_type = WireType.VARINT  # Uses wire type 0

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%" PRIu32, {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(name, force, "add_uint32_field")

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 3  # field ID + 3 bytes typical varint


@register_type(14)
class EnumType(TypeInfo):
    @property
    def cpp_type(self) -> str:
        return f"enums::{self._field.type_name[1:]}"

    @property
    def decode_varint(self) -> str:
        return f"static_cast<{self.cpp_type}>(value.as_uint32())"

    default_value = ""
    wire_type = WireType.VARINT  # Uses wire type 0

    @property
    def encode_func(self) -> str:
        return "encode_uint32"

    @property
    def encode_content(self) -> str:
        return f"buffer.{self.encode_func}({self.number}, static_cast<uint32_t>(this->{self.field_name}));"

    def dump(self, name: str) -> str:
        o = f"out.append(proto_enum_to_string<{self.cpp_type}>({name}));"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(
            name, force, "add_enum_field", f"static_cast<uint32_t>({name})"
        )

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 1  # field ID + 1 byte typical enum


@register_type(15)
class SFixed32Type(TypeInfo):
    cpp_type = "int32_t"
    default_value = "0"
    decode_32bit = "value.as_sfixed32()"
    encode_func = "encode_sfixed32"
    wire_type = WireType.FIXED32  # Uses wire type 5

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%" PRId32, {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        field_id_size = self.calculate_field_id_size()
        return f"ProtoSize::add_sfixed32_field(total_size, {field_id_size}, {name});"

    def get_fixed_size_bytes(self) -> int:
        return 4

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 4  # field ID + 4 bytes fixed


@register_type(16)
class SFixed64Type(TypeInfo):
    cpp_type = "int64_t"
    default_value = "0"
    decode_64bit = "value.as_sfixed64()"
    encode_func = "encode_sfixed64"
    wire_type = WireType.FIXED64  # Uses wire type 1

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%lld", {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        field_id_size = self.calculate_field_id_size()
        return f"ProtoSize::add_sfixed64_field(total_size, {field_id_size}, {name});"

    def get_fixed_size_bytes(self) -> int:
        return 8

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 8  # field ID + 8 bytes fixed


@register_type(17)
class SInt32Type(TypeInfo):
    cpp_type = "int32_t"
    default_value = "0"
    decode_varint = "value.as_sint32()"
    encode_func = "encode_sint32"
    wire_type = WireType.VARINT  # Uses wire type 0

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%" PRId32, {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(name, force, "add_sint32_field")

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 3  # field ID + 3 bytes typical varint


@register_type(18)
class SInt64Type(TypeInfo):
    cpp_type = "int64_t"
    default_value = "0"
    decode_varint = "value.as_sint64()"
    encode_func = "encode_sint64"
    wire_type = WireType.VARINT  # Uses wire type 0

    def dump(self, name: str) -> str:
        o = f'snprintf(buffer, sizeof(buffer), "%lld", {name});\n'
        o += "out.append(buffer);"
        return o

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        return self._get_simple_size_calculation(name, force, "add_sint64_field")

    def get_estimated_size(self) -> int:
        return self.calculate_field_id_size() + 3  # field ID + 3 bytes typical varint


class FixedArrayRepeatedType(TypeInfo):
    """Special type for fixed-size repeated fields using std::array.

    Fixed arrays are only supported for encoding (SOURCE_SERVER) since we cannot
    control how many items we receive when decoding.
    """

    def __init__(self, field: descriptor.FieldDescriptorProto, size: int) -> None:
        super().__init__(field)
        self.array_size = size
        # Create the element type info
        validate_field_type(field.type, field.name)
        self._ti: TypeInfo = TYPE_INFO[field.type](field)

    @property
    def cpp_type(self) -> str:
        return f"std::array<{self._ti.cpp_type}, {self.array_size}>"

    @property
    def reference_type(self) -> str:
        return f"{self.cpp_type} &"

    @property
    def const_reference_type(self) -> str:
        return f"const {self.cpp_type} &"

    @property
    def wire_type(self) -> WireType:
        """Get the wire type for this fixed array field."""
        return self._ti.wire_type

    @property
    def public_content(self) -> list[str]:
        # Just the array member, no index needed since we don't decode
        return [f"{self.cpp_type} {self.field_name}{{}};"]

    # No decode methods needed - fixed arrays don't support decoding
    # The base class TypeInfo already returns None for all decode properties

    @property
    def encode_content(self) -> str:
        # Helper to generate encode statement for a single element
        def encode_element(element: str) -> str:
            if isinstance(self._ti, EnumType):
                return f"buffer.{self._ti.encode_func}({self.number}, static_cast<uint32_t>({element}), true);"
            else:
                return f"buffer.{self._ti.encode_func}({self.number}, {element}, true);"

        # Unroll small arrays for efficiency
        if self.array_size == 1:
            return encode_element(f"this->{self.field_name}[0]")
        elif self.array_size == 2:
            return (
                encode_element(f"this->{self.field_name}[0]")
                + "\n  "
                + encode_element(f"this->{self.field_name}[1]")
            )

        # Use loops for larger arrays
        o = f"for (const auto &it : this->{self.field_name}) {{\n"
        o += f"  {encode_element('it')}\n"
        o += "}"
        return o

    @property
    def dump_content(self) -> str:
        o = f"for (const auto &it : this->{self.field_name}) {{\n"
        o += f'  out.append("  {self.name}: ");\n'
        o += indent(self._ti.dump("it")) + "\n"
        o += '  out.append("\\n");\n'
        o += "}\n"
        return o

    def dump(self, name: str) -> str:
        # This is used when dumping the array itself (not its elements)
        # Since dump_content handles the iteration, this is not used directly
        return ""

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        # For fixed arrays, we always encode all elements

        # Special case for single-element arrays - no loop needed
        if self.array_size == 1:
            return self._ti.get_size_calculation(f"{name}[0]", True)

        # Special case for 2-element arrays - unroll the calculation
        if self.array_size == 2:
            return (
                self._ti.get_size_calculation(f"{name}[0]", True)
                + "\n  "
                + self._ti.get_size_calculation(f"{name}[1]", True)
            )

        # Use loops for larger arrays
        o = f"for (const auto &it : {name}) {{\n"
        o += f"  {self._ti.get_size_calculation('it', True)}\n"
        o += "}"
        return o

    def get_estimated_size(self) -> int:
        # For fixed arrays, estimate underlying type size * array size
        underlying_size = self._ti.get_estimated_size()
        return underlying_size * self.array_size


class RepeatedTypeInfo(TypeInfo):
    def __init__(self, field: descriptor.FieldDescriptorProto) -> None:
        super().__init__(field)
        # For repeated fields, we need to get the base type info
        # but we can't call create_field_type_info as it would cause recursion
        # So we extract just the type creation logic
        if (
            field.type == 12
            and (fixed_size := get_field_opt(field, pb.fixed_array_size)) is not None
        ):
            self._ti: TypeInfo = FixedArrayBytesType(field, fixed_size)
            return

        validate_field_type(field.type, field.name)
        self._ti: TypeInfo = TYPE_INFO[field.type](field)

    @property
    def cpp_type(self) -> str:
        return f"std::vector<{self._ti.cpp_type}>"

    @property
    def reference_type(self) -> str:
        return f"{self.cpp_type} &"

    @property
    def const_reference_type(self) -> str:
        return f"const {self.cpp_type} &"

    @property
    def wire_type(self) -> WireType:
        """Get the wire type for this repeated field.

        For repeated fields, we use the same wire type as the underlying field.
        """
        return self._ti.wire_type

    @property
    def decode_varint_content(self) -> str:
        content = self._ti.decode_varint
        if content is None:
            return None
        return (
            f"case {self.number}: this->{self.field_name}.push_back({content}); break;"
        )

    @property
    def decode_length_content(self) -> str:
        content = self._ti.decode_length
        if content is None and isinstance(self._ti, MessageType):
            # Special handling for non-template message decoding
            return f"case {self.number}: this->{self.field_name}.emplace_back(); value.decode_to_message(this->{self.field_name}.back()); break;"
        if content is None:
            return None
        return (
            f"case {self.number}: this->{self.field_name}.push_back({content}); break;"
        )

    @property
    def decode_32bit_content(self) -> str:
        content = self._ti.decode_32bit
        if content is None:
            return None
        return (
            f"case {self.number}: this->{self.field_name}.push_back({content}); break;"
        )

    @property
    def decode_64bit_content(self) -> str:
        content = self._ti.decode_64bit
        if content is None:
            return None
        return (
            f"case {self.number}: this->{self.field_name}.push_back({content}); break;"
        )

    @property
    def _ti_is_bool(self) -> bool:
        # std::vector is specialized for bool, reference does not work
        return isinstance(self._ti, BoolType)

    @property
    def encode_content(self) -> str:
        o = f"for (auto {'' if self._ti_is_bool else '&'}it : this->{self.field_name}) {{\n"
        if isinstance(self._ti, EnumType):
            o += f"  buffer.{self._ti.encode_func}({self.number}, static_cast<uint32_t>(it), true);\n"
        else:
            o += f"  buffer.{self._ti.encode_func}({self.number}, it, true);\n"
        o += "}"
        return o

    @property
    def dump_content(self) -> str:
        o = f"for (const auto {'' if self._ti_is_bool else '&'}it : this->{self.field_name}) {{\n"
        o += f'  out.append("  {self.name}: ");\n'
        o += indent(self._ti.dump("it")) + "\n"
        o += '  out.append("\\n");\n'
        o += "}\n"
        return o

    def dump(self, _: str):
        pass

    def get_size_calculation(self, name: str, force: bool = False) -> str:
        # For repeated fields, we always need to pass force=True to the underlying type's calculation
        # This is because the encode method always sets force=true for repeated fields
        if isinstance(self._ti, MessageType):
            # For repeated messages, use the dedicated helper that handles iteration internally
            field_id_size = self._ti.calculate_field_id_size()
            o = f"ProtoSize::add_repeated_message(total_size, {field_id_size}, {name});"
            return o

        # For other repeated types, use the underlying type's size calculation with force=True
        o = f"if (!{name}.empty()) {{\n"

        # Check if this is a fixed-size type by seeing if it has a fixed byte count
        num_bytes = self._ti.get_fixed_size_bytes()
        if num_bytes is not None:
            # Fixed types have constant size per element, so we can multiply
            field_id_size = self._ti.calculate_field_id_size()
            # Pre-calculate the total bytes per element
            bytes_per_element = field_id_size + num_bytes
            o += f"  total_size += {name}.size() * {bytes_per_element};\n"
        else:
            # Other types need the actual value
            o += f"  for (const auto {'' if self._ti_is_bool else '&'}it : {name}) {{\n"
            o += f"    {self._ti.get_size_calculation('it', True)}\n"
            o += "  }\n"
        o += "}"
        return o

    def get_estimated_size(self) -> int:
        # For repeated fields, estimate underlying type size * 2 (assume 2 items typically)
        underlying_size = (
            self._ti.get_estimated_size()
            if hasattr(self._ti, "get_estimated_size")
            else 8
        )
        return underlying_size * 2


def build_type_usage_map(
    file_desc: descriptor.FileDescriptorProto,
) -> tuple[dict[str, str | None], dict[str, str | None], dict[str, int], set[str]]:
    """Build mappings for both enums and messages to their ifdefs based on usage.

    Returns:
        tuple: (enum_ifdef_map, message_ifdef_map, message_source_map, used_messages)
    """
    enum_ifdef_map: dict[str, str | None] = {}
    message_ifdef_map: dict[str, str | None] = {}
    message_source_map: dict[str, int] = {}

    # Build maps of which types are used by which messages
    enum_usage: dict[
        str, set[str]
    ] = {}  # enum_name -> set of message names that use it
    message_usage: dict[
        str, set[str]
    ] = {}  # message_name -> set of message names that use it
    used_messages: set[str] = set()  # Track which messages are actually used

    # Build message name to ifdef mapping for quick lookup
    message_to_ifdef: dict[str, str | None] = {
        msg.name: get_opt(msg, pb.ifdef) for msg in file_desc.message_type
    }

    # Analyze field usage
    # Also track field_ifdef for message types
    message_field_ifdefs: dict[
        str, set[str | None]
    ] = {}  # message_name -> set of field_ifdefs that use it

    for message in file_desc.message_type:
        # Skip deprecated messages entirely
        if message.options.deprecated:
            continue

        for field in message.field:
            # Skip deprecated fields when tracking enum usage
            if field.options.deprecated:
                continue

            type_name = field.type_name.split(".")[-1] if field.type_name else None
            if not type_name:
                continue

            # Track enum usage (only from non-deprecated fields)
            if field.type == 14:  # TYPE_ENUM
                enum_usage.setdefault(type_name, set()).add(message.name)
            # Track message usage
            elif field.type == 11:  # TYPE_MESSAGE
                message_usage.setdefault(type_name, set()).add(message.name)
                # Also track the field_ifdef if present
                field_ifdef = get_field_opt(field, pb.field_ifdef)
                message_field_ifdefs.setdefault(type_name, set()).add(field_ifdef)
                used_messages.add(type_name)

    # Helper to get unique ifdef from a set of messages
    def get_unique_ifdef(message_names: set[str]) -> str | None:
        ifdefs: set[str] = {
            message_to_ifdef[name]
            for name in message_names
            if message_to_ifdef.get(name)
        }
        return ifdefs.pop() if len(ifdefs) == 1 else None

    # Build enum ifdef map
    for enum in file_desc.enum_type:
        if enum.name in enum_usage:
            enum_ifdef_map[enum.name] = get_unique_ifdef(enum_usage[enum.name])
        else:
            enum_ifdef_map[enum.name] = None

    # Build message ifdef map
    for message in file_desc.message_type:
        # Explicit ifdef takes precedence
        explicit_ifdef = message_to_ifdef.get(message.name)
        if explicit_ifdef:
            message_ifdef_map[message.name] = explicit_ifdef
        elif message.name in message_usage:
            # Inherit ifdef if all parent messages have the same one
            if parent_ifdef := get_unique_ifdef(message_usage[message.name]):
                message_ifdef_map[message.name] = parent_ifdef
            elif message.name in message_field_ifdefs:
                # If no parent message ifdef, check if all fields using this message have the same field_ifdef
                field_ifdefs = message_field_ifdefs[message.name] - {None}
                message_ifdef_map[message.name] = (
                    field_ifdefs.pop() if len(field_ifdefs) == 1 else None
                )
            else:
                message_ifdef_map[message.name] = None
        else:
            message_ifdef_map[message.name] = None

    # Second pass: propagate ifdefs recursively
    # Keep iterating until no more changes are made
    changed = True
    iterations = 0
    while changed and iterations < 10:  # Add safety limit
        changed = False
        iterations += 1
        for message in file_desc.message_type:
            # Skip if already has an ifdef
            if message_ifdef_map.get(message.name):
                continue

            # Check if this message is used by other messages
            if message.name not in message_usage:
                continue

            # Get ifdefs from all messages that use this one
            parent_ifdefs: set[str] = {
                message_ifdef_map.get(parent)
                for parent in message_usage[message.name]
                if message_ifdef_map.get(parent)
            }

            # If all parents have the same ifdef, inherit it
            if len(parent_ifdefs) == 1 and None not in parent_ifdefs:
                message_ifdef_map[message.name] = parent_ifdefs.pop()
                changed = True

    # Build message source map
    # First pass: Get explicit sources for messages with source option or id
    for msg in file_desc.message_type:
        # Skip deprecated messages
        if msg.options.deprecated:
            continue

        if msg.options.HasExtension(pb.source):
            # Explicit source option takes precedence
            message_source_map[msg.name] = get_opt(msg, pb.source, SOURCE_BOTH)
        elif msg.options.HasExtension(pb.id):
            # Service messages (with id) default to SOURCE_BOTH
            message_source_map[msg.name] = SOURCE_BOTH
            # Service messages are always used
            used_messages.add(msg.name)

    # Second pass: Determine sources for embedded messages based on their usage
    for msg in file_desc.message_type:
        if msg.name in message_source_map:
            continue  # Already has explicit source

        if msg.name in message_usage:
            # Get sources from all parent messages that use this one
            parent_sources = {
                message_source_map[parent]
                for parent in message_usage[msg.name]
                if parent in message_source_map
            }

            # Combine parent sources
            if not parent_sources:
                # No parent has explicit source, default to encode-only
                message_source_map[msg.name] = SOURCE_SERVER
            elif len(parent_sources) > 1:
                # Multiple different sources or SOURCE_BOTH present
                message_source_map[msg.name] = SOURCE_BOTH
            else:
                # Inherit single parent source
                message_source_map[msg.name] = parent_sources.pop()
        else:
            # Not used by any message and no explicit source - default to encode-only
            message_source_map[msg.name] = SOURCE_SERVER

    return (
        enum_ifdef_map,
        message_ifdef_map,
        message_source_map,
        used_messages,
    )


def build_enum_type(desc, enum_ifdef_map) -> tuple[str, str, str]:
    """Builds the enum type.

    Args:
        desc: The enum descriptor
        enum_ifdef_map: Mapping of enum names to their ifdefs

    Returns:
        tuple: (header_content, cpp_content, dump_cpp_content)
    """
    name = desc.name

    out = f"enum {name} : uint32_t {{\n"
    for v in desc.value:
        out += f"  {v.name} = {v.number},\n"
    out += "};\n"

    # Regular cpp file has no enum content anymore
    cpp = ""

    # Dump cpp content for enum string conversion
    dump_cpp = f"template<> const char *proto_enum_to_string<enums::{name}>(enums::{name} value) {{\n"
    dump_cpp += "  switch (value) {\n"
    for v in desc.value:
        dump_cpp += f"    case enums::{v.name}:\n"
        dump_cpp += f'      return "{v.name}";\n'
    dump_cpp += "    default:\n"
    dump_cpp += '      return "UNKNOWN";\n'
    dump_cpp += "  }\n"
    dump_cpp += "}\n"

    return out, cpp, dump_cpp


def calculate_message_estimated_size(desc: descriptor.DescriptorProto) -> int:
    """Calculate estimated size for a complete message based on typical values."""
    total_size = 0

    for field in desc.field:
        # Skip deprecated fields
        if field.options.deprecated:
            continue

        ti = create_field_type_info(field)

        # Add estimated size for this field
        total_size += ti.get_estimated_size()

    return total_size


def build_message_type(
    desc: descriptor.DescriptorProto,
    base_class_fields: dict[str, list[descriptor.FieldDescriptorProto]],
    message_source_map: dict[str, int],
) -> tuple[str, str, str]:
    public_content: list[str] = []
    protected_content: list[str] = []
    decode_varint: list[str] = []
    decode_length: list[str] = []
    decode_32bit: list[str] = []
    decode_64bit: list[str] = []
    encode: list[str] = []
    dump: list[str] = []
    size_calc: list[str] = []

    # Check if this message has a base class
    base_class = get_base_class(desc)
    common_field_names = set()
    if base_class and base_class_fields and base_class in base_class_fields:
        common_field_names = {f.name for f in base_class_fields[base_class]}

    # Get message ID if it's a service message
    message_id: int | None = get_opt(desc, pb.id)

    # Get source direction to determine if we need decode/encode methods
    source = message_source_map[desc.name]
    needs_decode = source in (SOURCE_BOTH, SOURCE_CLIENT)
    needs_encode = source in (SOURCE_BOTH, SOURCE_SERVER)

    # Add MESSAGE_TYPE method if this is a service message
    if message_id is not None:
        # Validate that message_id fits in uint8_t
        if message_id > 255:
            raise ValueError(
                f"Message ID {message_id} for {desc.name} exceeds uint8_t maximum (255)"
            )

        # Add static constexpr for message type
        public_content.append(f"static constexpr uint8_t MESSAGE_TYPE = {message_id};")

        # Add estimated size constant
        estimated_size = calculate_message_estimated_size(desc)
        # Validate that estimated_size fits in uint8_t
        if estimated_size > 255:
            raise ValueError(
                f"Estimated size {estimated_size} for {desc.name} exceeds uint8_t maximum (255)"
            )
        public_content.append(
            f"static constexpr uint8_t ESTIMATED_SIZE = {estimated_size};"
        )

        # Add message_name method inline in header
        public_content.append("#ifdef HAS_PROTO_MESSAGE_DUMP")
        snake_name = camel_to_snake(desc.name)
        public_content.append(
            f'const char *message_name() const override {{ return "{snake_name}"; }}'
        )
        public_content.append("#endif")

    for field in desc.field:
        # Skip deprecated fields completely
        if field.options.deprecated:
            continue

        # Validate that fixed_array_size is only used in encode-only messages
        if (
            needs_decode
            and field.label == 3
            and get_field_opt(field, pb.fixed_array_size) is not None
        ):
            raise ValueError(
                f"Message '{desc.name}' uses fixed_array_size on field '{field.name}' "
                f"but has source={SOURCE_NAMES[source]}. "
                f"Fixed arrays are only supported for SOURCE_SERVER (encode-only) messages "
                f"since we cannot trust or control the number of items received from clients."
            )

        ti = create_field_type_info(field, needs_decode, needs_encode)

        # Skip field declarations for fields that are in the base class
        # but include their encode/decode logic
        if field.name not in common_field_names:
            # Check for field_ifdef option
            field_ifdef = None
            if field.options.HasExtension(pb.field_ifdef):
                field_ifdef = field.options.Extensions[pb.field_ifdef]

            if ti.protected_content:
                protected_content.extend(
                    wrap_with_ifdef(ti.protected_content, field_ifdef)
                )
            if ti.public_content:
                public_content.extend(wrap_with_ifdef(ti.public_content, field_ifdef))

        # Only collect encode logic if this message needs it
        if needs_encode:
            # Check for field_ifdef option
            field_ifdef = None
            if field.options.HasExtension(pb.field_ifdef):
                field_ifdef = field.options.Extensions[pb.field_ifdef]

            encode.extend(wrap_with_ifdef(ti.encode_content, field_ifdef))
            size_calc.extend(
                wrap_with_ifdef(
                    ti.get_size_calculation(f"this->{ti.field_name}"), field_ifdef
                )
            )

        # Only collect decode methods if this message needs them
        if needs_decode:
            # Check for field_ifdef option for decode as well
            field_ifdef = None
            if field.options.HasExtension(pb.field_ifdef):
                field_ifdef = field.options.Extensions[pb.field_ifdef]

            if ti.decode_varint_content:
                decode_varint.extend(
                    wrap_with_ifdef(ti.decode_varint_content, field_ifdef)
                )
            if ti.decode_length_content:
                decode_length.extend(
                    wrap_with_ifdef(ti.decode_length_content, field_ifdef)
                )
            if ti.decode_32bit_content:
                decode_32bit.extend(
                    wrap_with_ifdef(ti.decode_32bit_content, field_ifdef)
                )
            if ti.decode_64bit_content:
                decode_64bit.extend(
                    wrap_with_ifdef(ti.decode_64bit_content, field_ifdef)
                )
        if ti.dump_content:
            # Check for field_ifdef option for dump as well
            field_ifdef = None
            if field.options.HasExtension(pb.field_ifdef):
                field_ifdef = field.options.Extensions[pb.field_ifdef]

            dump.extend(wrap_with_ifdef(ti.dump_content, field_ifdef))

    cpp = ""
    if decode_varint:
        o = f"bool {desc.name}::decode_varint(uint32_t field_id, ProtoVarInt value) {{\n"
        o += "  switch (field_id) {\n"
        o += indent("\n".join(decode_varint), "    ") + "\n"
        o += "    default: return false;\n"
        o += "  }\n"
        o += "  return true;\n"
        o += "}\n"
        cpp += o
        prot = "bool decode_varint(uint32_t field_id, ProtoVarInt value) override;"
        protected_content.insert(0, prot)
    if decode_length:
        o = f"bool {desc.name}::decode_length(uint32_t field_id, ProtoLengthDelimited value) {{\n"
        o += "  switch (field_id) {\n"
        o += indent("\n".join(decode_length), "    ") + "\n"
        o += "    default: return false;\n"
        o += "  }\n"
        o += "  return true;\n"
        o += "}\n"
        cpp += o
        prot = "bool decode_length(uint32_t field_id, ProtoLengthDelimited value) override;"
        protected_content.insert(0, prot)
    if decode_32bit:
        o = f"bool {desc.name}::decode_32bit(uint32_t field_id, Proto32Bit value) {{\n"
        o += "  switch (field_id) {\n"
        o += indent("\n".join(decode_32bit), "    ") + "\n"
        o += "    default: return false;\n"
        o += "  }\n"
        o += "  return true;\n"
        o += "}\n"
        cpp += o
        prot = "bool decode_32bit(uint32_t field_id, Proto32Bit value) override;"
        protected_content.insert(0, prot)
    if decode_64bit:
        o = f"bool {desc.name}::decode_64bit(uint32_t field_id, Proto64Bit value) {{\n"
        o += "  switch (field_id) {\n"
        o += indent("\n".join(decode_64bit), "    ") + "\n"
        o += "    default: return false;\n"
        o += "  }\n"
        o += "  return true;\n"
        o += "}\n"
        cpp += o
        prot = "bool decode_64bit(uint32_t field_id, Proto64Bit value) override;"
        protected_content.insert(0, prot)

    # Only generate encode method if this message needs encoding and has fields
    if needs_encode and encode:
        o = f"void {desc.name}::encode(ProtoWriteBuffer buffer) const {{"
        if len(encode) == 1 and len(encode[0]) + len(o) + 3 < 120:
            o += f" {encode[0]} "
        else:
            o += "\n"
            o += indent("\n".join(encode)) + "\n"
        o += "}\n"
        cpp += o
        prot = "void encode(ProtoWriteBuffer buffer) const override;"
        public_content.append(prot)
    # If no fields to encode or message doesn't need encoding, the default implementation in ProtoMessage will be used

    # Add calculate_size method only if this message needs encoding and has fields
    if needs_encode and size_calc:
        o = f"void {desc.name}::calculate_size(uint32_t &total_size) const {{"
        # For a single field, just inline it for simplicity
        if len(size_calc) == 1 and len(size_calc[0]) + len(o) + 3 < 120:
            o += f" {size_calc[0]} "
        else:
            # For multiple fields
            o += "\n"
            o += indent("\n".join(size_calc)) + "\n"
        o += "}\n"
        cpp += o
        prot = "void calculate_size(uint32_t &total_size) const override;"
        public_content.append(prot)
    # If no fields to calculate size for or message doesn't need encoding, the default implementation in ProtoMessage will be used

    # dump_to method declaration in header
    prot = "#ifdef HAS_PROTO_MESSAGE_DUMP\n"
    prot += "void dump_to(std::string &out) const override;\n"
    prot += "#endif\n"
    public_content.append(prot)

    # dump_to implementation will go in dump_cpp
    dump_impl = f"void {desc.name}::dump_to(std::string &out) const {{"
    if dump:
        if len(dump) == 1 and len(dump[0]) + len(dump_impl) + 3 < 120:
            dump_impl += f" {dump[0]} "
        else:
            dump_impl += "\n"
            dump_impl += "  __attribute__((unused)) char buffer[64];\n"
            dump_impl += f'  out.append("{desc.name} {{\\n");\n'
            dump_impl += indent("\n".join(dump)) + "\n"
            dump_impl += '  out.append("}");\n'
    else:
        o2 = f'out.append("{desc.name} {{}}");'
        if len(dump_impl) + len(o2) + 3 < 120:
            dump_impl += f" {o2} "
        else:
            dump_impl += "\n"
            dump_impl += f"  {o2}\n"
    dump_impl += "}\n"

    if base_class:
        out = f"class {desc.name} : public {base_class} {{\n"
    else:
        # Determine inheritance based on whether the message needs decoding
        base_class = "ProtoDecodableMessage" if needs_decode else "ProtoMessage"
        out = f"class {desc.name} : public {base_class} {{\n"
    out += " public:\n"
    out += indent("\n".join(public_content)) + "\n"
    out += "\n"
    out += " protected:\n"
    out += indent("\n".join(protected_content))
    if len(protected_content) > 0:
        out += "\n"
    out += "};\n"

    # Build dump_cpp content with dump_to implementation
    dump_cpp = dump_impl

    return out, cpp, dump_cpp


SOURCE_BOTH = 0
SOURCE_SERVER = 1
SOURCE_CLIENT = 2

SOURCE_NAMES = {
    SOURCE_BOTH: "SOURCE_BOTH",
    SOURCE_SERVER: "SOURCE_SERVER",
    SOURCE_CLIENT: "SOURCE_CLIENT",
}

RECEIVE_CASES: dict[int, tuple[str, str | None]] = {}

ifdefs: dict[str, str] = {}


def get_opt(
    desc: descriptor.DescriptorProto,
    opt: descriptor.MessageOptions,
    default: Any = None,
) -> Any:
    """Get the option from the descriptor."""
    if not desc.options.HasExtension(opt):
        return default
    return desc.options.Extensions[opt]


def get_field_opt(
    field: descriptor.FieldDescriptorProto,
    opt: descriptor.FieldOptions,
    default: Any = None,
) -> Any:
    """Get the option from a field descriptor."""
    if not field.options.HasExtension(opt):
        return default
    return field.options.Extensions[opt]


def get_base_class(desc: descriptor.DescriptorProto) -> str | None:
    """Get the base_class option from a message descriptor."""
    if not desc.options.HasExtension(pb.base_class):
        return None
    return desc.options.Extensions[pb.base_class]


def collect_messages_by_base_class(
    messages: list[descriptor.DescriptorProto],
) -> dict[str, list[descriptor.DescriptorProto]]:
    """Group messages by their base_class option."""
    base_class_groups = {}

    for msg in messages:
        base_class = get_base_class(msg)
        if base_class:
            if base_class not in base_class_groups:
                base_class_groups[base_class] = []
            base_class_groups[base_class].append(msg)

    return base_class_groups


def find_common_fields(
    messages: list[descriptor.DescriptorProto],
) -> list[descriptor.FieldDescriptorProto]:
    """Find fields that are common to all messages in the list."""
    if not messages:
        return []

    # Start with fields from the first message (excluding deprecated fields)
    first_msg_fields = {
        field.name: field for field in messages[0].field if not field.options.deprecated
    }
    common_fields = []

    # Check each field to see if it exists in all messages with same type
    # Field numbers can vary between messages - derived classes handle the mapping
    for field_name, field in first_msg_fields.items():
        is_common = True

        for msg in messages[1:]:
            found = False
            for other_field in msg.field:
                # Skip deprecated fields
                if other_field.options.deprecated:
                    continue
                if (
                    other_field.name == field_name
                    and other_field.type == field.type
                    and other_field.label == field.label
                ):
                    found = True
                    break

            if not found:
                is_common = False
                break

        if is_common:
            common_fields.append(field)

    # Sort by field number to maintain order
    common_fields.sort(key=lambda f: f.number)
    return common_fields


def get_common_field_ifdef(
    field_name: str, messages: list[descriptor.DescriptorProto]
) -> str | None:
    """Get the field_ifdef option if it's consistent across all messages.

    Args:
        field_name: Name of the field to check
        messages: List of messages that contain this field

    Returns:
        The field_ifdef string if all messages have the same value, None otherwise
    """
    field_ifdefs = {
        get_field_opt(field, pb.field_ifdef)
        for msg in messages
        if (field := next((f for f in msg.field if f.name == field_name), None))
    }

    # Return the ifdef only if all messages agree on the same value
    return field_ifdefs.pop() if len(field_ifdefs) == 1 else None


def build_base_class(
    base_class_name: str,
    common_fields: list[descriptor.FieldDescriptorProto],
    messages: list[descriptor.DescriptorProto],
    message_source_map: dict[str, int],
) -> tuple[str, str, str]:
    """Build the base class definition and implementation."""
    public_content = []
    protected_content = []

    # Determine if any message using this base class needs decoding/encoding
    needs_decode = any(
        message_source_map.get(msg.name, SOURCE_BOTH) in (SOURCE_BOTH, SOURCE_CLIENT)
        for msg in messages
    )
    needs_encode = any(
        message_source_map.get(msg.name, SOURCE_BOTH) in (SOURCE_BOTH, SOURCE_SERVER)
        for msg in messages
    )

    # For base classes, we only declare the fields but don't handle encode/decode
    # The derived classes will handle encoding/decoding with their specific field numbers
    for field in common_fields:
        ti = create_field_type_info(field, needs_decode, needs_encode)

        # Get field_ifdef if it's consistent across all messages
        field_ifdef = get_common_field_ifdef(field.name, messages)

        # Only add field declarations, not encode/decode logic
        if ti.protected_content:
            protected_content.extend(wrap_with_ifdef(ti.protected_content, field_ifdef))
        if ti.public_content:
            public_content.extend(wrap_with_ifdef(ti.public_content, field_ifdef))

    # Build header
    parent_class = "ProtoDecodableMessage" if needs_decode else "ProtoMessage"
    out = f"class {base_class_name} : public {parent_class} {{\n"
    out += " public:\n"

    # Add destructor with override
    public_content.insert(0, f"~{base_class_name}() override = default;")

    # Base classes don't implement encode/decode/calculate_size
    # Derived classes handle these with their specific field numbers
    cpp = ""

    out += indent("\n".join(public_content)) + "\n"
    out += "\n"
    out += " protected:\n"
    out += indent("\n".join(protected_content))
    if protected_content:
        out += "\n"
    out += "};\n"

    # No implementation needed for base classes
    dump_cpp = ""

    return out, cpp, dump_cpp


def generate_base_classes(
    base_class_groups: dict[str, list[descriptor.DescriptorProto]],
    message_source_map: dict[str, int],
) -> tuple[str, str, str]:
    """Generate all base classes."""
    all_headers = []
    all_cpp = []
    all_dump_cpp = []

    for base_class_name, messages in base_class_groups.items():
        # Find common fields
        common_fields = find_common_fields(messages)

        if common_fields:
            # Generate base class
            header, cpp, dump_cpp = build_base_class(
                base_class_name, common_fields, messages, message_source_map
            )
            all_headers.append(header)
            all_cpp.append(cpp)
            all_dump_cpp.append(dump_cpp)

    return "\n".join(all_headers), "\n".join(all_cpp), "\n".join(all_dump_cpp)


def build_service_message_type(
    mt: descriptor.DescriptorProto,
    message_source_map: dict[str, int],
) -> tuple[str, str] | None:
    """Builds the service message type."""
    # Skip deprecated messages
    if mt.options.deprecated:
        return None

    snake = camel_to_snake(mt.name)
    id_: int | None = get_opt(mt, pb.id)
    if id_ is None:
        return None

    source: int = message_source_map.get(mt.name, SOURCE_BOTH)

    ifdef: str | None = get_opt(mt, pb.ifdef)
    log: bool = get_opt(mt, pb.log, True)
    hout = ""
    cout = ""

    # Store ifdef for later use
    if ifdef is not None:
        ifdefs[str(mt.name)] = ifdef

    if source in (SOURCE_BOTH, SOURCE_SERVER):
        # Don't generate individual send methods anymore
        # The generic send_message method will be used instead
        pass
    if source in (SOURCE_BOTH, SOURCE_CLIENT):
        # Only add ifdef when we're actually generating content
        if ifdef is not None:
            hout += f"#ifdef {ifdef}\n"
        # Generate receive
        func = f"on_{snake}"
        hout += f"virtual void {func}(const {mt.name} &value){{}};\n"
        case = ""
        case += f"{mt.name} msg;\n"
        case += "msg.decode(msg_data, msg_size);\n"
        if log:
            case += "#ifdef HAS_PROTO_MESSAGE_DUMP\n"
            case += f'ESP_LOGVV(TAG, "{func}: %s", msg.dump().c_str());\n'
            case += "#endif\n"
        case += f"this->{func}(msg);\n"
        case += "break;"
        # Store the ifdef with the case for later use
        RECEIVE_CASES[id_] = (case, ifdef)

        # Only close ifdef if we opened it
        if ifdef is not None:
            hout += "#endif\n"

    return hout, cout


def main() -> None:
    """Main function to generate the C++ classes."""
    cwd = Path(__file__).resolve().parent
    root = cwd.parent.parent / "esphome" / "components" / "api"
    prot_file = root / "api.protoc"
    call(["protoc", "-o", str(prot_file), "-I", str(root), "api.proto"])
    proto_content = prot_file.read_bytes()

    # pylint: disable-next=no-member
    d = descriptor.FileDescriptorSet.FromString(proto_content)

    file = d.file[0]
    content = FILE_HEADER
    content += """\
#pragma once

#include "esphome/core/defines.h"

#include "proto.h"

namespace esphome {
namespace api {

"""

    cpp = FILE_HEADER
    cpp += """\
    #include "api_pb2.h"
    #include "esphome/core/log.h"
    #include "esphome/core/helpers.h"
    #include <cstring>

namespace esphome {
namespace api {

"""

    # Initialize dump cpp content
    dump_cpp = FILE_HEADER
    dump_cpp += """\
#include "api_pb2.h"
#include "esphome/core/helpers.h"

#include <cinttypes>

#ifdef HAS_PROTO_MESSAGE_DUMP

namespace esphome {
namespace api {

"""

    content += "namespace enums {\n\n"

    # Build dynamic ifdef mappings for both enums and messages
    enum_ifdef_map, message_ifdef_map, message_source_map, used_messages = (
        build_type_usage_map(file)
    )

    # Simple grouping of enums by ifdef
    current_ifdef = None

    for enum in file.enum_type:
        # Skip deprecated enums
        if enum.options.deprecated:
            continue

        s, c, dc = build_enum_type(enum, enum_ifdef_map)
        enum_ifdef = enum_ifdef_map.get(enum.name)

        # Handle ifdef changes
        if enum_ifdef != current_ifdef:
            if current_ifdef is not None:
                content += "#endif\n"
                dump_cpp += "#endif\n"
            if enum_ifdef is not None:
                content += f"#ifdef {enum_ifdef}\n"
                dump_cpp += f"#ifdef {enum_ifdef}\n"
            current_ifdef = enum_ifdef

        content += s
        cpp += c
        dump_cpp += dc

    # Close last ifdef
    if current_ifdef is not None:
        content += "#endif\n"
        dump_cpp += "#endif\n"

    content += "\n}  // namespace enums\n\n"

    mt = file.message_type

    # Collect messages by base class
    base_class_groups = collect_messages_by_base_class(mt)

    # Find common fields for each base class
    base_class_fields = {}
    for base_class_name, messages in base_class_groups.items():
        common_fields = find_common_fields(messages)
        if common_fields:
            base_class_fields[base_class_name] = common_fields

    # Generate base classes
    if base_class_fields:
        base_headers, base_cpp, base_dump_cpp = generate_base_classes(
            base_class_groups, message_source_map
        )
        content += base_headers
        cpp += base_cpp
        dump_cpp += base_dump_cpp

    # Generate message types with base class information
    # Simple grouping by ifdef
    current_ifdef = None

    for m in mt:
        # Skip deprecated messages
        if m.options.deprecated:
            continue

        # Skip messages that aren't used (unless they have an ID/service message)
        if m.name not in used_messages and not m.options.HasExtension(pb.id):
            continue

        s, c, dc = build_message_type(m, base_class_fields, message_source_map)
        msg_ifdef = message_ifdef_map.get(m.name)

        # Handle ifdef changes
        if msg_ifdef != current_ifdef:
            if current_ifdef is not None:
                content += "#endif\n"
                if cpp:
                    cpp += "#endif\n"
                if dump_cpp:
                    dump_cpp += "#endif\n"
            if msg_ifdef is not None:
                content += f"#ifdef {msg_ifdef}\n"
                cpp += f"#ifdef {msg_ifdef}\n"
                dump_cpp += f"#ifdef {msg_ifdef}\n"
            current_ifdef = msg_ifdef

        content += s
        cpp += c
        dump_cpp += dc

    # Close last ifdef
    if current_ifdef is not None:
        content += "#endif\n"
        cpp += "#endif\n"
        dump_cpp += "#endif\n"

    content += """\

}  // namespace api
}  // namespace esphome
"""
    cpp += """\

}  // namespace api
}  // namespace esphome
"""

    dump_cpp += """\

}  // namespace api
}  // namespace esphome

#endif  // HAS_PROTO_MESSAGE_DUMP
"""

    with open(root / "api_pb2.h", "w", encoding="utf-8") as f:
        f.write(content)

    with open(root / "api_pb2.cpp", "w", encoding="utf-8") as f:
        f.write(cpp)

    with open(root / "api_pb2_dump.cpp", "w", encoding="utf-8") as f:
        f.write(dump_cpp)

    hpp = FILE_HEADER
    hpp += """\
#pragma once

#include "esphome/core/defines.h"

#include "api_pb2.h"

namespace esphome {
namespace api {

"""

    cpp = FILE_HEADER
    cpp += """\
#include "api_pb2_service.h"
#include "esphome/core/log.h"

namespace esphome {
namespace api {

static const char *const TAG = "api.service";

"""

    class_name = "APIServerConnectionBase"

    hpp += f"class {class_name} : public ProtoService {{\n"
    hpp += " public:\n"

    # Add logging helper method declaration
    hpp += "#ifdef HAS_PROTO_MESSAGE_DUMP\n"
    hpp += " protected:\n"
    hpp += "  void log_send_message_(const char *name, const std::string &dump);\n"
    hpp += " public:\n"
    hpp += "#endif\n\n"

    # Add non-template send_message method
    hpp += "  bool send_message(const ProtoMessage &msg, uint8_t message_type) {\n"
    hpp += "#ifdef HAS_PROTO_MESSAGE_DUMP\n"
    hpp += "    this->log_send_message_(msg.message_name(), msg.dump());\n"
    hpp += "#endif\n"
    hpp += "    return this->send_message_(msg, message_type);\n"
    hpp += "  }\n\n"

    # Add logging helper method implementation to cpp
    cpp += "#ifdef HAS_PROTO_MESSAGE_DUMP\n"
    cpp += f"void {class_name}::log_send_message_(const char *name, const std::string &dump) {{\n"
    cpp += '  ESP_LOGVV(TAG, "send_message %s: %s", name, dump.c_str());\n'
    cpp += "}\n"
    cpp += "#endif\n\n"

    for mt in file.message_type:
        obj = build_service_message_type(mt, message_source_map)
        if obj is None:
            continue
        hout, cout = obj
        hpp += indent(hout) + "\n"
        cpp += cout

    cases = list(RECEIVE_CASES.items())
    cases.sort()
    hpp += " protected:\n"
    hpp += "  void read_message(uint32_t msg_size, uint32_t msg_type, uint8_t *msg_data) override;\n"
    out = f"void {class_name}::read_message(uint32_t msg_size, uint32_t msg_type, uint8_t *msg_data) {{\n"
    out += "  switch (msg_type) {\n"
    for i, (case, ifdef) in cases:
        if ifdef is not None:
            out += f"#ifdef {ifdef}\n"
        c = f"    case {i}: {{\n"
        c += indent(case, "      ") + "\n"
        c += "    }"
        out += c + "\n"
        if ifdef is not None:
            out += "#endif\n"
    out += "    default:\n"
    out += "      break;\n"
    out += "  }\n"
    out += "}\n"
    cpp += out
    hpp += "};\n"

    serv = file.service[0]
    class_name = "APIServerConnection"
    hpp += "\n"
    hpp += f"class {class_name} : public {class_name}Base {{\n"
    hpp += " public:\n"
    hpp_protected = ""
    cpp += "\n"

    m = serv.method[0]
    for m in serv.method:
        func = m.name
        inp = m.input_type[1:]
        ret = m.output_type[1:]
        is_void = ret == "void"
        snake = camel_to_snake(inp)
        on_func = f"on_{snake}"
        needs_conn = get_opt(m, pb.needs_setup_connection, True)
        needs_auth = get_opt(m, pb.needs_authentication, True)

        ifdef = message_ifdef_map.get(inp, ifdefs.get(inp, None))

        if ifdef is not None:
            hpp += f"#ifdef {ifdef}\n"
            hpp_protected += f"#ifdef {ifdef}\n"
            cpp += f"#ifdef {ifdef}\n"

        hpp_protected += f"  void {on_func}(const {inp} &msg) override;\n"
        hpp += f"  virtual {ret} {func}(const {inp} &msg) = 0;\n"
        cpp += f"void {class_name}::{on_func}(const {inp} &msg) {{\n"

        # Start with authentication/connection check if needed
        if needs_auth or needs_conn:
            # Determine which check to use
            if needs_auth:
                check_func = "this->check_authenticated_()"
            else:
                check_func = "this->check_connection_setup_()"

            body = f"if ({check_func}) {{\n"

            # Add the actual handler code, indented
            handler_body = ""
            if is_void:
                handler_body = f"this->{func}(msg);\n"
            else:
                handler_body = f"{ret} ret = this->{func}(msg);\n"
                handler_body += (
                    f"if (!this->send_message(ret, {ret}::MESSAGE_TYPE)) {{\n"
                )
                handler_body += "  this->on_fatal_error();\n"
                handler_body += "}\n"

            body += indent(handler_body) + "\n"
            body += "}\n"
        else:
            # No auth check needed, just call the handler
            body = ""
            if is_void:
                body += f"this->{func}(msg);\n"
            else:
                body += f"{ret} ret = this->{func}(msg);\n"
                body += f"if (!this->send_message(ret, {ret}::MESSAGE_TYPE)) {{\n"
                body += "  this->on_fatal_error();\n"
                body += "}\n"

        cpp += indent(body) + "\n" + "}\n"

        if ifdef is not None:
            hpp += "#endif\n"
            hpp_protected += "#endif\n"
            cpp += "#endif\n"

    hpp += " protected:\n"
    hpp += hpp_protected
    hpp += "};\n"

    hpp += """\

}  // namespace api
}  // namespace esphome
"""
    cpp += """\

}  // namespace api
}  // namespace esphome
"""

    with open(root / "api_pb2_service.h", "w", encoding="utf-8") as f:
        f.write(hpp)

    with open(root / "api_pb2_service.cpp", "w", encoding="utf-8") as f:
        f.write(cpp)

    prot_file.unlink()

    try:
        import clang_format

        def exec_clang_format(path: Path) -> None:
            clang_format_path = os.path.join(
                os.path.dirname(clang_format.__file__), "data", "bin", "clang-format"
            )
            call([clang_format_path, "-i", path])

        exec_clang_format(root / "api_pb2_service.h")
        exec_clang_format(root / "api_pb2_service.cpp")
        exec_clang_format(root / "api_pb2.h")
        exec_clang_format(root / "api_pb2.cpp")
        exec_clang_format(root / "api_pb2_dump.cpp")
    except ImportError:
        pass


if __name__ == "__main__":
    sys.exit(main())
