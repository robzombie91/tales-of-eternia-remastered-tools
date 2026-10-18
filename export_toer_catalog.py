#!/usr/bin/env python3
"""Export TOER resource name records to CSV and/or JSON (read-only)."""
import argparse
import csv
import json
import struct
from pathlib import Path

RECORD_START = 0xC43E8  # Observed in a Tales of Eternia Remastered TOER sample
RECORD_SIZE = 40


def crc32_custom(data: bytes, polynomial: int) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (polynomial if crc & 1 else 0)
    return (~crc) & 0xFFFFFFFF


def hash_filename(filename: bytes) -> int:
    return (crc32_custom(filename, 0x10215681) << 32) | crc32_custom(filename, 0x56811021)


def cstring(blob: bytes, ptr: int, label: str) -> bytes:
    if not 0 <= ptr < len(blob):
        raise ValueError(f"{label} pointer outside file: 0x{ptr:X}")
    end = blob.find(b"\x00", ptr)
    if end < 0:
        raise ValueError(f"unterminated {label} at 0x{ptr:X}")
    return blob[ptr:end]


def parse(blob: bytes, strict: bool = True):
    if len(blob) < 0x18 or blob[:4] != b"TOER":
        raise ValueError("Not a TOER file")
    count = struct.unpack_from("<I", blob, 0x10)[0]
    end = RECORD_START + count * RECORD_SIZE
    if count == 0 or end > len(blob):
        raise ValueError(f"Record range beyond file: {count} records, end 0x{end:X}")
    rows = []
    errors = []
    for idx in range(count):
        at = RECORD_START + idx * RECORD_SIZE
        packed, flags, id_ptr, name_ptr, hash64 = struct.unpack_from("<QQQQQ", blob, at)
        try:
            identifier = cstring(blob, id_ptr, "identifier").decode("utf-8")
            name_bytes = cstring(blob, name_ptr, "filename")
            filename = name_bytes.decode("utf-8")
            expected = hash_filename(name_bytes)
            verified = expected == hash64
            if not verified:
                raise ValueError(f"hash mismatch: stored {hash64:016X}, computed {expected:016X}")
            rows.append({
                "index": idx,
                "record_offset": f"0x{at:X}",
                "identifier": identifier,
                "filename": filename,
                "hash64": f"{hash64:016X}",
                "packed_field": f"0x{packed:016X}",
                "flags_field": f"0x{flags:016X}",
                "identifier_offset": f"0x{id_ptr:X}",
                "filename_offset": f"0x{name_ptr:X}",
            })
        except (ValueError, UnicodeDecodeError) as exc:
            errors.append(f"record {idx} at 0x{at:X}: {exc}")
            if strict:
                raise ValueError(errors[-1]) from exc
    return count, rows, errors


def main():
    cli = argparse.ArgumentParser(description="Export TOER asset catalog as CSV/JSON")
    cli.add_argument("toer", type=Path, help="Extracted TOER resource binary")
    cli.add_argument("--output", type=Path, default=Path("toer_catalog"), help="Output filename stem or directory")
    cli.add_argument("--format", choices=("csv", "json", "both"), default="both")
    cli.add_argument("--continue-on-error", action="store_true", help="Skip bad records and report them")
    args = cli.parse_args()
    if not args.toer.is_file():
        cli.error(f"Input not found: {args.toer}")
    out = args.output
    if out.exists() and out.is_dir():
        out = out / "toer_catalog"
    elif out.suffix in (".csv", ".json"):
        out = out.with_suffix("")
    try:
        count, rows, errors = parse(args.toer.read_bytes(), strict=not args.continue_on_error)
    except ValueError as err:
        cli.error(str(err))
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.format in ("csv", "both"):
        with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["index", "record_offset", "identifier", "filename", "hash64", "packed_field", "flags_field", "identifier_offset", "filename_offset"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSV: {out.with_suffix('.csv')}")
    if args.format in ("json", "both"):
        with out.with_suffix(".json").open("w", encoding="utf-8") as fh:
            json.dump({"source": str(args.toer), "records_declared": count, "records_verified": len(rows), "errors": errors, "resources": rows}, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print(f"JSON: {out.with_suffix('.json')}")
    print(f"Verified: {len(rows)}/{count}; errors: {len(errors)}")
    for error in errors[:10]:
        print("ERROR:", error)
    if errors:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
