#!/usr/bin/env python3
"""Read-only extractor for the ZARC v2 layout observed in Tales of Eternia Remastered.

No third-party Python modules required. Extracted filenames are hash identifiers,
not recovered original names. Use only on archives you are entitled to access.
"""
import argparse
import json
import lzma
import os
from pathlib import Path
import struct
import sys

HEADER = struct.Struct('>4s9I')
HEADER_SIZE = HEADER.size
RECORD_SIZE = 24
MAX_BLOCK_SIZE = 16 * 1024 * 1024

class ArchiveError(Exception):
    pass


def decode_record(data):
    return {
        'id': data[:8].hex().upper(),
        'size': int.from_bytes(data[8:13], 'big'),
        'unknown': int.from_bytes(data[13:17], 'big'),
        'first_block': int.from_bytes(data[17:20], 'big'),
        'offset_units': int.from_bytes(data[20:24], 'big'),
    }


def read_exact(fp, n):
    b = fp.read(n)
    if len(b) != n:
        raise ArchiveError(f'Unexpected end of archive: wanted {n} bytes, got {len(b)}')
    return b


def load_index(fp):
    archive_size = fp.seek(0, os.SEEK_END)
    fp.seek(0)
    if archive_size < HEADER_SIZE:
        raise ArchiveError('Archive is smaller than its 40-byte header')
    magic, version, meta_end, stride, count, unknown_14, unknown_18, block_size, align, unknown_24 = HEADER.unpack(read_exact(fp, HEADER_SIZE))
    if magic != b'ZARC':
        raise ArchiveError('Not a ZARC archive')
    if version != 2:
        raise ArchiveError(f'Unsupported ZARC version {version}; only version 2 has been tested')
    if stride != RECORD_SIZE:
        raise ArchiveError(f'Unsupported index stride {stride}; expected 24')
    if not (0 < block_size <= MAX_BLOCK_SIZE):
        raise ArchiveError(f'Implausible block size {block_size}')
    if not (0 < align <= 65536 and (align & (align-1)) == 0):
        raise ArchiveError(f'Implausible alignment {align}')
    if count > 10_000_000:
        raise ArchiveError('Implausible entry count')
    index_end = HEADER_SIZE + count * stride
    if not (index_end <= meta_end <= archive_size):
        raise ArchiveError('Invalid metadata boundaries')
    records = [decode_record(read_exact(fp, stride)) for _ in range(count)]
    table_bytes = meta_end - index_end
    if table_bytes % 2:
        raise ArchiveError('Block-size table has odd length')
    table_data = read_exact(fp, table_bytes)
    block_lengths = [v[0] or block_size for v in struct.iter_unpack('>H', table_data)]
    for i, r in enumerate(records):
        r['block_count'] = (r['size'] + block_size - 1) // block_size
        start, end = r['first_block'], r['first_block'] + r['block_count']
        if end > len(block_lengths):
            raise ArchiveError(f'Record {i} block index runs past block table')
        if (offset := r['offset_units'] * align) < meta_end or offset > archive_size:
            raise ArchiveError(f'Record {i} has invalid data offset 0x{offset:X}')
        stored = sum(block_lengths[start:end])
        if offset + stored > archive_size:
            raise ArchiveError(f'Record {i} extends beyond end of archive')
        r['stored_bytes'] = stored
        r['offset_bytes'] = offset
        if i:
            prev = records[i-1]
            expected = prev['offset_bytes'] + ((prev['stored_bytes'] + align - 1) // align) * align
            if expected != offset:
                raise ArchiveError(f'Records {i-1} and {i} have inconsistent consecutive offsets')
    return {
        'version': version,
        'metadata_end': meta_end,
        'block_size': block_size,
        'alignment': align,
        'entries': records,
        'block_lengths': block_lengths,
        'archive_size': archive_size,
        'unknown_header_fields': [unknown_14, unknown_18, unknown_24],
    }


def extract_one(fp, r, lengths, block_size, output):
    first = r['first_block']
    remaining = r['size']
    fp.seek(r['offset_bytes'])
    # Write to a partial file, rename only after all blocks validate.
    partial = output.with_name(output.name + '.partial')
    try:
        with partial.open('xb') as dest:
            for i in range(r['block_count']):
                n = lengths[first+i]
                raw = read_exact(fp, n)
                expected = min(block_size, remaining)
                if n == block_size:
                    decoded = raw
                else:
                    try:
                        decoded = lzma.decompress(raw, format=lzma.FORMAT_ALONE)
                    except lzma.LZMAError as exc:
                        raise ArchiveError(f'Block {i}: LZMA decoding failed: {exc}') from exc
                if len(decoded) != expected:
                    raise ArchiveError(f'Block {i}: decompressed to {len(decoded)} bytes; expected {expected}')
                dest.write(decoded)
                remaining -= len(decoded)
            if remaining != 0:
                raise ArchiveError(f'File incomplete: {remaining} bytes remaining')
        # The caller refuses existing destinations, so do not overwrite anything.
        if output.exists():
            raise ArchiveError(f'Output file already exists: {output}')
        partial.rename(output)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help='Path to DATA.zarc')
    parser.add_argument('-o', '--output', type=Path, default=Path.home() / 'zarc_extracted', help='Destination directory (default: ~/zarc_extracted)')
    parser.add_argument('--limit', type=int, default=None, help='Extract only first N entries (for testing)')
    args = parser.parse_args()
    if args.limit is not None and args.limit < 0:
        parser.error('--limit must be nonnegative')
    if not args.archive.is_file():
        parser.error(f'Archive not found: {args.archive}')
    if args.output.resolve() == args.archive.resolve() or args.output.resolve() == args.archive.resolve().parent:
        parser.error('Choose a separate output folder, not the archive path or its parent')
    with args.archive.open('rb') as fp:
        meta = load_index(fp)
        records = meta['entries']
        todo = records[:args.limit] if args.limit is not None else records
        print(f'ZARC v{meta["version"]}: {len(records)} entries; block size {meta["block_size"]:,}; alignment {meta["alignment"]}')
        print(f'Archive: {meta["archive_size"]:,} bytes | metadata ends at 0x{meta["metadata_end"]:X}')
        print(f'Extracting {len(todo)} entries to: {args.output.resolve()}')
        args.output.mkdir(parents=True, exist_ok=True)
        success = failed = skipped = 0
        manifest = []
        for i, r in enumerate(todo):
            filename = f'{i:04d}_{r["id"]}.bin'
            output = args.output / filename
            status = 'ok'
            if output.exists():
                status = 'skipped_existing'
                skipped += 1
            else:
                try:
                    extract_one(fp, r, meta['block_lengths'], meta['block_size'], output)
                    success += 1
                except (ArchiveError, OSError, EOFError) as exc:
                    status = f'error: {exc}'
                    failed += 1
                    print(f'ERROR #{i:04d} ({r["id"]}): {exc}', file=sys.stderr, flush=True)
            manifest.append({'index': i, 'filename': filename, **r, 'status': status})
            if (i+1) % 50 == 0 or i+1 == len(todo):
                print(f'Progress: {i+1}/{len(todo)} | ok={success} skipped={skipped} failed={failed}', flush=True)
        manifest_path = args.output / 'manifest.json'
        if manifest_path.exists():
            print(f'Existing manifest preserved: {manifest_path}')
        else:
            manifest_path.write_text(json.dumps({
                'archive': str(args.archive.resolve()),
                'header': {k:v for k,v in meta.items() if k not in ('entries', 'block_lengths')},
                'resources': manifest,
            }, indent=2) + '\n', encoding='utf-8')
        print(f'Done. Extracted={success}, skipped={skipped}, failed={failed}')
        print('Names are archive identifiers; original filenames are not known.')
        return 1 if failed else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except ArchiveError as exc:
        print(f'Invalid/unsupported archive: {exc}', file=sys.stderr)
        raise SystemExit(2)
