#!/usr/bin/env python3

import argparse
import os
import struct
import sys
import typing


def abort(msg: str):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)

def abort_unless(cond: bool, msg: str):
    if not cond:
        abort(msg)


def read_bytes(data: bytes, offset: int, size: int) -> bytes:
    abort_unless(offset + size < len(data), "unexpected EOF")
    return data[offset:offset+size]

def read_string(data: bytes, offset: int, size: int = -1, encoding_name: str = "ascii") -> str:
    if size == -1:
        out = b""
        i = 0
        while (char := read_bytes(data, offset+i, 1)) != b'\x00':
            out += char
            i += 1
    else:
        out = read_bytes(data, offset, size)
    
    return out.decode(encoding_name)

def read_signature(data: bytes, offset: int, size: int, expected: str) -> str:
    signature = read_string(data, offset, size)
    abort_unless(signature == expected, f"file signature was {signature}, expected {expected}")
    return signature

def read_u8(data: bytes, offset: int) -> int:
    out = read_bytes(data, offset, 1)
    return int(*struct.unpack("<B", out))

def read_u16(data: bytes, offset: int) -> int:
    out = read_bytes(data, offset, 2)
    return int(*struct.unpack("<H", out))

def read_u32(data: bytes, offset: int) -> int:
    out = read_bytes(data, offset, 4)
    return int(*struct.unpack("<I", out))

def read_u64(data: bytes, offset: int) -> int:
    out = read_bytes(data, offset, 8)
    return int(*struct.unpack("<Q", out))

def align(offset: int, alignment: int):
    delta = (-offset % alignment + alignment) % alignment
    return offset + delta


def main():
    parser = argparse.ArgumentParser(description="extract PFS0 file to directory")
    parser.add_argument("infile")
    parser.add_argument("outdir", nargs="?")
    # parser.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()

    abort_unless(os.path.isfile(args.infile), "input file doesn't exist")
    outdir = os.path.splitext(args.infile)[0] if args.outdir is None else args.outdir

    os.makedirs(outdir, exist_ok=True)

    with open(args.infile, "rb") as f:
        contents = f.read()
    
    read_signature(contents, 0x0, 4, "PFS0")
    entry_count = read_u32(contents, 0x4)
    string_pool_size = read_u32(contents, 0x8)
    string_pool_offset = 0x10 + 0x18 * entry_count
    data_offset = string_pool_offset + string_pool_size

    for i in range(entry_count):
        entry_offset = 0x10 + 0x18 * i
        offset = read_u64(contents, entry_offset)
        size = read_u64(contents, entry_offset + 0x8)
        string_offset = read_u32(contents, entry_offset + 0x10)

        string = read_string(contents, string_pool_offset + string_offset)
        entry_data_offset = data_offset + offset

        with open(os.path.join(outdir, string), "wb") as f:
            f.write(contents[entry_data_offset:entry_data_offset+size])


if __name__ == "__main__":
    main()
