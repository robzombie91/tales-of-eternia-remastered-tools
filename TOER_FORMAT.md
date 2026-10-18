# TOER master catalog — validated layout (2026-10-18)

**Scope:** the specific 5,411,080-byte extracted file `1009_FB41681A91008172.bin` from one PC build. This catalog maps names/IDs/hashes; it does **not** contain proven offsets of `.tim`/`.pmd` asset bytes. Parsing is implemented by `export_toer_catalog.py`; its complete export yielded **50,237 rows and zero validation errors**.

## Header and pointer tables

| File offset | Layout | Interpretation |
|---|---|---|
| `0x00` | ASCII `TOER` | Magic |
| `0x10` | LE uint32 `50237` | Catalog record count |
| `0x18` | 50,237 × LE uint64 | Index A: absolute record offsets ordered by identifier text |
| `0x62200` | 50,237 × LE uint64 | Index B: absolute record offsets ordered by 64-bit filename hash |
| `0xC43E8` | 50,237 × 40 bytes | Fixed-width record table |
| `0x2AED70` | beginning of string region | End of record table |

Each 40-byte record consists of five LE uint64 values: `packed`, `resource_type`, `identifier_pointer`, `filename_pointer`, `filename_hash`. The `packed` value equals `(resource_id << 32) | zero_based_record_index`. All pointers from both indexes referenced valid records; all 50,237 record names passed hash validation.

Resource types: `0` = 4,481 entries with blank identifiers (`.bin`, `.anp`, `.clt`); `1` = 33,508 `.tim` entries; `2` = 12,248 `.pmd` entries. The **45,756 named** resource IDs encode `[8-bit group][8-bit type][16-bit sequence]`; groups 1–8 show gapless group-wide sequences. There are **47,362 unique filename hashes**; 462 duplicate-hash groups contain 3,337 records and all duplicates in each group share the same filename (no observed different-name collisions).

## Name hash

The custom 64-bit hash is `(crc_high << 32) | crc_low`. For each CRC, initialize 32-bit state `0xffffffff`, XOR each input filename byte, run eight right shifts with conditional XOR of the respective polynomial, then complement on completion. High polynomial `0x10215681`, low polynomial `0x56811021`. The exact implementation and byte encoding should be taken from the verified `export_toer_catalog.py` before porting; do not replace it with a standard CRC32 implementation.

## Other `TOER` resources

30 further `TOER`-signature files were observed, distinct from the master catalog: 20 with a reported count of 27,239 and 10 with 276. These appear to be multilingual indexed localization/string databases, not copies of the catalog. Their record/string layout is less fully established; avoid treating a suspected 64-byte record stride as universally proven. A survey identified readable strings across these resources. The precise language mapping and all header fields need confirmation.

## Open issues

- **Unsolved:** mapping catalog filenames and IDs to the actual stored nested payloads in extracted ZARC resources.
- **Unsolved:** decoding the numbered-container `0x03` payload codec; see `NUMBERED_CONTAINERS.md`.
- Neither `.tim` nor `.pmd` files have yet been demonstrated to be individually reconstructed from these containers.
- Do not infer that the 50,237 catalog rows are 50,237 independently stored ZARC members (only 1,183 outer members exist).
