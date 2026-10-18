# ZARC v2 Format — Observed PC Archive

**Status:** functional, evidence-based specification for **one** observed `DATA.zarc` from *Tales of Eternia Remastered* (PC). This is **not** an official specification; other archive variants/builds are untested.

## Reference and validation

- Observed archive path: `Tales of Eternia Remastered_Data/StreamingAssets/Archive/DATA.zarc`.
- Archive size: **916,771,200 bytes**.
- Archive identifier: ASCII `ZARC`, reported version `2`.
- Indexed resources: **1,183**.
- Across two read-only extraction runs, **1,183/1,183** entries were extracted without reported failures. First version rejected 125 padded final blocks; `extract_zarc_v2.py` corrected the final-block handling.
- Validation was based on Ghidra inspection of `GameNative.dll`, manual Python checks and real archive extraction. Output was **not** compared byte-for-byte against an independent original-file set.

## On-disk layout (reference archive)

```text
0x00000000       40-byte ZARC header
0x00000028       1,183 × 24-byte index entries
0x00006F10       2-byte big-endian stored-block-length table
0x0000F8FA       Metadata ends (63,738 bytes from file start)
0x0000F8FA       6 bytes of observed EE padding
0x0000F900       First stored resource (128-byte aligned)
...              Resource data, with 128-byte end-of-resource alignment
```

### Header: `>4s9I` (40 bytes)

All nine numeric header fields are **32-bit unsigned, big-endian**. The signature is ASCII.

| Offset | Size | Observed value | Interpretation / status |
| --- | ---: | ---: | --- |
| `0x00` | 4 | `ZARC` | Signature — verified |
| `0x04` | 4 | `2` | Version — strongly supported |
| `0x08` | 4 | `63,738` (`0xF8FA`) | Metadata end, absolute byte offset — verified by loader |
| `0x0C` | 4 | `24` | Index record stride in bytes — verified |
| `0x10` | 4 | `1,183` | Number of index records — verified |
| `0x14` | 4 | `2,000` | Unknown |
| `0x18` | 4 | `1` | Unknown |
| `0x1C` | 4 | `65,536` | Logical block size — verified |
| `0x20` | 4 | `128` | Resource alignment in bytes — verified by observed offsets |
| `0x24` | 4 | `1` | Unknown |

`GameNative.dll` function `FUN_18026f2b0` decodes the 40-byte header; `FUN_180272510` validates `ZARC`, checks the configured record stride and loads the remaining metadata.

### Index record: 24 bytes

Fixed-width, packed, big-endian fields:

| Relative byte offsets | Width | Purpose |
| --- | ---: | --- |
| `0x00–0x07` | 8 | 64-bit archive lookup identifier |
| `0x08–0x0C` | 5 | Logical uncompressed resource size |
| `0x0D–0x10` | 4 | Unknown metadata (may be type/flags or other property; do not assume) |
| `0x11–0x13` | 3 | Starting index into global block-size table |
| `0x14–0x17` | 4 | Absolute stored resource offset, measured in alignment units |

For a record with `size = S`, `first_block = B` and `offset_units = U`:

```python
block_count = (S + block_size - 1) // block_size
file_offset = U * alignment
```

The decoder was traced to `FUN_18026f440`. `FUN_18026ea00` searches an index by its 64-bit identifier. The on-disk identifiers in the observed archive are strictly increasing. The exact relationship between readable asset paths and those identifiers remains **unresolved**.

### Stored block-size table

The block-size table starts immediately after the index:

```python
index_end = 40 + record_count * record_stride  # 0x6F10
block_table_bytes = metadata_end - index_end     # 35,306
```

It consists of **17,653** two-byte big-endian values (`35,306 / 2`). For the observed archive:

- `0` represents a stored **65,536-byte raw block**.
- Nonzero values represent a stored compressed block's byte length.
- Compressed blocks tested use the standard Python-compatible `lzma.FORMAT_ALONE` stream layout, including the 13-byte LZMA-Alone header.
- Read all blocks of a resource **consecutively**, with no 128-byte padding inserted between individual blocks.
- After the resource, the next resource begins at the next **128-byte** aligned position.

The first 1,182 consecutive resource offset transitions agreed **exactly** with summed stored block lengths rounded to 128-byte alignment.

**Caution about last blocks:** The final logical block may decompress to the full 65,536 bytes even when the declared resource length needs fewer bytes. The output must keep only the remaining logical bytes. The v1 extractor incorrectly treated this as an error for 125 resources.

### Example: first resource

| Attribute | Value |
| --- | --- |
| Identifier | `E001331793365D5B` |
| Declared logical size | 130,316 bytes |
| Starting block index | 0 |
| Stored offset units | 498 |
| Absolute archive offset | `498 * 128 = 63,744` (`0xF900`) |
| Blocks | 2 |
| Stored lengths | 61,645 + 59,710 bytes |
| Decoded lengths | 65,536 + 64,780 bytes |

The first block begins with LZMA-Alone header bytes `5D 00 00 00 04 00 00 01 00 00 00 00 00`, and `lzma.decompress(..., format=lzma.FORMAT_ALONE)` successfully returned 65,536 bytes.

### Extraction algorithm (read-only)

1. Validate header and archive length.
2. Read `count` fixed-size records and the global block-size table.
3. For each record, determine `block_count`, first block index and absolute stored offset.
4. For each block: read its stored length; copy raw bytes if its table value is zero, otherwise LZMA-Alone-decompress.
5. Append at most the logical bytes remaining in that resource; reject insufficient decoded data and impossible decoded sizes.
6. Verify output size, write to a separate destination, and skip alignment padding before the next resource.

`extract_zarc_v2.py` implements this process with checks and writes a `manifest_v2.json`. It skips preexisting output files **without verifying their integrity**. Use a clean output directory when independent verification is needed.

## Open questions / limitations

- Meanings of header fields `0x14`, `0x18`, `0x24` and the four-byte record field at `0x0D`.
- Name/key generation in the real runtime, despite identified CRC-derived hashing routines (`FUN_18026f570`/`FUN_18026f640`). Prior tests of guessed paths failed to match the archive keys.
- Whether other ZARC versions or PC builds change widths, encoding, compression, or alignment.
- Whether raw final blocks always store a full logical block; trimming of excess bytes is supported in the observed archive.
- Archive rebuilding/repacking and game acceptance of replacements: **not implemented**.
- Some extracted resources are themselves proprietary nested formats, including `TOER`; see `TOER_FORMAT.md`.

## Safe reproducibility

Use your own copy of the game and do not redistribute original archives, extracted assets, game binaries, or copyrighted content. Add tests with synthetic fixtures and record results when validating another build.
