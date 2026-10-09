#!/usr/bin/env python3
"""Convert a verified Simplemma 2.0.0 wheel to native research resources.

Data licensing is separate from the MIT software license. Generated resources
are intentionally excluded from Git and are not bundled in either shipping app.
The canonical variant closes case-insensitive mapping components so every
dictionary edge has one matching search key. This can increase false positives;
evaluate retrieval independently rather than scoring those edges as accuracy.
"""
import argparse
import collections
import hashlib
import json
import lzma
import pathlib
import struct
import unicodedata
import zipfile

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


def normalized(value):
    return unicodedata.normalize("NFC", value).lower()


def canonicalize(pairs):
    parent = {}
    frequencies = collections.Counter()
    terminals = set()

    def find(word):
        parent.setdefault(word, word)
        root = word
        while parent[root] != root:
            root = parent[root]
        while parent[word] != word:
            next_word = parent[word]
            parent[word] = root
            word = next_word
        return root

    for word, lemma in pairs:
        word, lemma = normalized(word), normalized(lemma)
        frequencies[lemma] += 1
        if word == lemma:
            terminals.add(lemma)
        left, right = find(word), find(lemma)
        if left != right:
            parent[left] = right
    representatives = {}
    for word in parent:
        root = find(word)
        score = (word not in terminals, -frequencies[word], len(word), word.encode())
        previous = representatives.get(root)
        if previous is None or score < previous[0]:
            representatives[root] = (score, word)
    return {word: representatives[find(word)][1] for word in parent}


def encode(mapping, output):
    items = sorted((k.encode(), v.encode()) for k, v in mapping.items() if k != v)
    blocks, offsets = bytearray(), []

    def varint(number):
        while number >= 128:
            blocks.append((number & 127) | 128)
            number >>= 7
        blocks.append(number)

    previous = b""
    for index, (key, value) in enumerate(items):
        if index % 32 == 0:
            offsets.append(len(blocks))
            previous = b""
        shared = 0
        while shared < min(len(key), len(previous)) and key[shared] == previous[shared]:
            shared += 1
        varint(shared)
        varint(len(key) - shared)
        blocks.extend(key[shared:])
        value_prefix = 0
        while value_prefix < min(len(key), len(value)) and key[value_prefix] == value[value_prefix]:
            value_prefix += 1
        varint(value_prefix)
        varint(len(value) - value_prefix)
        blocks.extend(value[value_prefix:])
        previous = key
    base = 16 + 4 * len(offsets)
    output.write_bytes(b"SML1" + struct.pack("<III", 32, len(offsets), len(items)) +
                       b"".join(struct.pack("<I", base + x) for x in offsets) + blocks)
    return len(items)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256(args.wheel.read_bytes()).hexdigest()
    if digest != WHEEL_SHA256:
        raise ValueError("Simplemma wheel checksum mismatch")
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"simplemma_version": "2.0.0", "wheel_sha256": digest, "languages": {}}
    with zipfile.ZipFile(args.wheel) as wheel:
        for language in ("de", "fr", "es"):
            pairs = list(decode(lzma.decompress(wheel.read(f"simplemma/strategies/dictionaries/data/{language}.plzma"))))
            # Exact/lowercase-key conflicts are reported rather than hidden.
            direct = {}
            for word, lemma in pairs:
                key = normalized(word)
                if word == key or key not in direct:
                    direct[key] = normalized(lemma)
            canonical = canonicalize(pairs)
            details = {"source_entries": len(pairs), "direct_keys": len(direct),
                       "canonical_nodes": len(canonical), "changed_from_direct": sum(canonical[k] != v for k, v in direct.items())}
            for variant, mapping in (("direct", direct), ("canonical", canonical)):
                path = args.output / f"{language}-{variant}.sml"
                details[variant] = {"mapped_entries": encode(mapping, path), "bytes": path.stat().st_size,
                                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            (args.output / f"{language}-mappings.json").write_text(json.dumps({"direct": direct, "canonical": canonical}, ensure_ascii=False))
            report["languages"][language] = details
    (args.output / "provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
