#!/usr/bin/env python3

import argparse
import enum
import io
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


def write_u8(fp: io.BufferedWriter, value: int):
    fp.write(struct.pack("<B", value))

def write_u16(fp: io.BufferedWriter, value: int):
    fp.write(struct.pack("<H", value))

def write_u32(fp: io.BufferedWriter, value: int):
    fp.write(struct.pack("<I", value))

def write_u64(fp: io.BufferedWriter, value: int):
    fp.write(struct.pack("<Q", value))

def write_bytes(fp: io.BufferedWriter, value: bytes):
    fp.write(value)

def write_string(fp: io.BufferedWriter, value: str, *, max_len: int = -1):
    if max_len > 0:
        value = value[:max_len]
        fp.write("{:\0<{max_len}}".format(value, max_len=max_len).encode("ascii"))
    else:
        fp.write(value.encode("ascii"))

def align(fp: io.BufferedWriter, alignment: int):
    delta = (-fp.tell() % alignment + alignment) % alignment
    fp.seek(delta, io.SEEK_CUR)


def main():
    parser = argparse.ArgumentParser(description="generate PFS0 file from directory")
    parser.add_argument("indir")
    parser.add_argument("outfile", nargs="?")
    # parser.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()

    abort_unless(os.path.isdir(args.indir), "input dir doesn't exist")
    outfile = f"{args.indir}.nsp" if args.outfile is None else args.outfile

    filenames = os.listdir(args.indir)
    entry_count = len(filenames)
    entries_offset = 0x10
    string_pool_offset = entries_offset + 0x18 * entry_count

    outf = open(outfile, "wb")

    # write filenames to string pool
    string_offsets = {}
    outf.seek(string_pool_offset)
    for filename in filenames:
        abort_unless(not os.path.isdir(os.path.join(args.indir, filename)), "input dir mustn't contain other directories")
        string_offsets[filename] = outf.tell() - string_pool_offset
        write_string(outf, filename)
        write_bytes(outf, b"\x00")
    align(outf, 0x10)
    data_offset = outf.tell()
    string_pool_size = data_offset - string_pool_offset
    
    # write file header
    outf.seek(0)
    write_string(outf, "PFS0")
    write_u32(outf, entry_count)
    write_u32(outf, string_pool_size)

    # write PFS0 entries
    entry_data_offset = data_offset
    for i, filename in enumerate(filenames):
        string_offset = string_offsets[filename]
        entry_offset = entries_offset + 0x18 * i

        outf.seek(entry_data_offset)
        with open(os.path.join(args.indir, filename), "rb") as f:
            while (chunk := f.read(0x100000)):
                write_bytes(outf, chunk)
        entry_size = outf.tell() - entry_data_offset

        outf.seek(entry_offset)
        write_u64(outf, entry_data_offset - data_offset)
        write_u64(outf, entry_size)
        write_u32(outf, string_offset)

        entry_data_offset += entry_size
            
if __name__ == "__main__":
    main()
