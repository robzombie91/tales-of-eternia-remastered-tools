# TOER reverse-engineering checkpoint — 2026-10-18

This checkpoint supersedes the *early/unsolved* TOER interpretations in the initial notes. Findings below are based on the user's verified experiments with extracted ZARC resources. The game installation is never modified by these tools.

## Extraction milestone

- `DATA.zarc`: 1,183 entries extracted successfully with `extract_zarc_v2.py`.
- Master TOER sample: `1009_FB41681A91008172.bin`, 5,411,080 bytes.
- Exporter `export_toer_catalog.py` produced 50,237 CSV/JSON rows, with 50,237/50,237 filename hashes matching and zero errors.

## Master TOER catalog

- Header at `0x00`: `TOER`.
- Little-endian count at `0x10`: 50,237.
- Two index arrays: each 50,237 × 8-byte little-endian absolute record pointers.
  - Index A at `0x18`: sorted by identifier strings, with empty identifiers first.
  - Index B at `0x62200`: sorted by 64-bit filename hashes.
  - All 100,474 pointers are aligned to valid records and both indexes individually contain 50,237 distinct record references.
- Record table at `0xC43E8`, 50,237 × 40-byte entries, ending exactly at `0x2AED70` (beginning of identifier string data).
- Record five little-endian 64-bit fields: `packed`, `resource_type`, `identifier_string_pointer`, `filename_string_pointer`, `filename_hash`.
- `packed = (resource_id << 32) | zero_based_record_index`; verified across all rows. Blank identifiers correspond to resource ID zero.
- `resource_type=0`: 4,481 rows with blank identifiers (`.bin` / `.anp` / `.clt`).
- `resource_type=1`: 33,508 named `.tim` rows.
- `resource_type=2`: 12,248 named `.pmd` rows.
- Named 32-bit resource IDs appear as `[8-bit group][8-bit type][16-bit group-wide sequential number]`, with types matching the record field and group sequence numbers contiguous and non-overlapping, for groups 1 through 8 (45,756 named rows).
- 47,362 unique hashes, 462 duplicate-hash groups spanning 3,337 records. All duplicate-hash groups share the same filename; no differing-name hash collision was found in this dataset.
- 64-bit filename hash is two custom 32-bit CRC-like functions (initial CRC `0xFFFFFFFF`, final bitwise inversion) concatenated high/low with polynomials `0x10215681` and `0x56811021`, respectively. See the exporter for reference implementation.

## Other TOER files

The ZARC inventory shows 30 more files beginning with `TOER`: ten with header word `0x08=276` and twenty with `0x08=27239`. For all 30, the header word at `0x10` is `count*8+16` and a pointer array begins at `0x18`. Sampled pointers refer to 64-byte-spaced structures, followed by readable strings (including `CHAR_NAME_*` in one sample). The 64-byte stride and string pointers are being validated with `analyze_zarc_resources.py` and should **not** yet be interpreted as asset payload records. Earlier manual analysis calculated the final record as `first_pointer + count*64`, accidentally entering the string region; the last record must be located by the *last actual index pointer* (or `first_pointer + (count-1)*64` only if validated).

## Numbered resources and native research (later findings)

See `NUMBERED_CONTAINERS.md` for the 890 structurally valid containers, 10,379 validated `0x03` framed records, codec tests and corrected analysis of the giant 179,648,624-byte section. Ghidra established that `FUN_1802740f0` calls the LZMA-Alone wrapper under `ZArcThreadMutex`; it is the **outer ZARC** decoder, not the nested codec. `Assembly-CSharp.dll` exposes Unity Addressables asset-loading constructs (`UgxAssetManager.LoadAsset<T>(uint addressableId)`), but the code path for the nested containers is not determined. No runtime-debugger capture has been performed.

## Not yet established

- Mapping TOER catalog filenames to extracted ZARC payload bytes.
- Semantics of all remaining header fields and string table encodings.
- Whether the six ZARC files starting with the ASCII bytes `PMD` contain actual standalone model data.
- Whether any `.tim` or `.pmd` contents can be extracted from a larger enclosing structure.

## Next workflow

Pause point as of 2026-10-18: the user is returning to playing the game. Future work should locate the consumer of the nine-byte `0x03` wrapper or capture one decoded sample at runtime; verify its decoded size against the wrapper and connect it to a catalog filename. **Do not restart broad prefix scans or continue the already-identified outer LZMA chain.** Do not commit proprietary extracted asset data or full catalog content without checking redistribution permissions.
