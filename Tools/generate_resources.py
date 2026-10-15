#!/usr/bin/env python3
"""Decode the pinned Simplemma wheel for production data generation.

The wheel checksum is verified by generate_bundled_resources.py before decoding.
Linguistic data licenses are separate from the MIT software license.
"""

WHEEL_SHA256 = "db33b15f5aed6485a748ce34d1f510ca760af2633289ab9a8493e2afa785c352"


def decode(data):
    assert data[:5] == b"SMFC1"
    reverse = data[5] & 1
    pos = 6

    def varint():
        nonlocal pos
        value = shift = 0
        while True:
            byte = data[pos]
            pos += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
            shift += 7

    count = varint()
    key = value = b""
    for _ in range(count):
        shared, length = varint(), varint()
        key = key[:shared] + data[pos:pos + length]
        pos += length
        trim = data[pos]
        pos += 1
        if trim != 254:
            length = varint()
            suffix = data[pos:pos + length]
            pos += length
            value = suffix if trim == 255 else key[:len(key) - trim] + suffix
        yield ((key[::-1] if reverse else key).decode(), (value[::-1] if reverse else value).decode())
    assert pos == len(data)
