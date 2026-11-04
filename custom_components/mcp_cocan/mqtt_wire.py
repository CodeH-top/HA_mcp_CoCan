"""Small independent protobuf wire codec for the documented public MQTT profile.

No generated vendor modules. Field numbers are protocol facts, not command IDs.
Only varints, fixed32/64 and length-delimited fields are accepted, with limits.
"""
from __future__ import annotations

MAX_PAYLOAD = 262144
# command -> (CommandRequest oneof field, CommandResponse oneof field)
COMMANDS = {
    0x11: (10, 20), 0x1A: (14, 24), 0x1B: (15, 25),
    0x43: (40, 50), 0x44: (41, 51), 0x48: (45, 55),
    0x49: (46, 56), 0x4A: (47, 57), 0x4C: (48, 58), 0x4D: (49, 59),
    0x5B: (56, 66), 0x5C: (57, 67), 0x5E: (53, 63),
    0x70: (80, 90), 0x72: (82, 92), 0x73: (83, 93), 0x7F: (91, 101),
    0x90: (100, 110), 0x91: (101, 111), 0x92: (16, 26),
}


def varint(value: int) -> bytes:
    if type(value) is not int or not 0 <= value < 2**64:
        raise ValueError('Invalid unsigned protobuf integer')
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def integer(field: int, value: int) -> bytes:
    return varint(field << 3) + varint(value)


def message(field: int, value: bytes) -> bytes:
    return varint((field << 3) | 2) + varint(len(value)) + value


def packed(field: int, values) -> bytes:
    return message(field, b''.join(varint(value) for value in values))


def decode(raw: bytes) -> dict[int, list[int | bytes]]:
    if not isinstance(raw, bytes) or len(raw) > MAX_PAYLOAD:
        raise ValueError('Invalid protobuf payload size')
    cursor = 0
    def read_varint():
        nonlocal cursor
        value = 0
        for offset in range(0, 70, 7):
            if cursor >= len(raw):
                raise ValueError('Truncated protobuf integer')
            byte = raw[cursor]
            cursor += 1
            value |= (byte & 127) << offset
            if byte < 128:
                if value >= 2**64:
                    raise ValueError('Overflow protobuf integer')
                return value
        raise ValueError('Overflow protobuf integer')
    result = {}
    count = 0
    while cursor < len(raw):
        count += 1
        if count > 4096:
            raise ValueError('Too many protobuf fields')
        tag = read_varint()
        field, wire = tag >> 3, tag & 7
        if not 0 < field < 2**29:
            raise ValueError('Invalid protobuf field')
        if wire == 0:
            value = read_varint()
        else:
            length = read_varint() if wire == 2 else {1: 8, 5: 4}.get(wire)
            if length is None or cursor + length > len(raw):
                raise ValueError('Invalid protobuf wire type or length')
            value = raw[cursor:cursor + length]
            cursor += length
        result.setdefault(field, []).append(value)
    return result


def scalar(fields, field, default=0):
    values = fields.get(field, [])
    if len(values) > 1:
        raise ValueError('Duplicate scalar field')
    value = values[0] if values else default
    if type(value) is not int:
        raise ValueError('Wrong scalar wire type')
    return value


def nested(fields, field, required=False):
    values = fields.get(field, [])
    if len(values) > 1 or (required and not values):
        raise ValueError('Missing or duplicate message field')
    return decode(values[0]) if values else {}


def text(fields, field):
    values = fields.get(field, [])
    if len(values) > 1 or (values and not isinstance(values[0], bytes)):
        raise ValueError('Invalid text field')
    return values[0].decode('utf-8')[:255] if values else ''


def version(fields):
    return '.'.join(str(scalar(fields, part)) for part in (1, 2, 3))


def version_tuple(value):
    parts = value.split('.')
    if len(parts) != 3 or any(not part.isdigit() or int(part) > 255 for part in parts):
        raise ValueError('Expected major.minor.patch, each 0-255')
    return tuple(int(part) for part in parts)


def encode_version(value):
    return b''.join(integer(i, part) for i, part in enumerate(version_tuple(value), 1))
