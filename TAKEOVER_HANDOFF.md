# Tales of Eternia Remastered — takeover handoff (2026-10-18)

**Goal:** Read-only extraction of named original `.tim` textures and `.pmd` models from the PC release, ideally starting with `TOE/Char/Main/Rid_01.tim`. **Current outcome: no verified `.tim`/`.pmd` asset extracted.** The nested `0x03` transform and link from catalog filename to payload are unresolved. Do not confuse complete inventories with end-to-end extraction.

## Confirmed findings (one user's PC build)

- **ZARC outer archive:** 916,771,200-byte `DATA.zarc`, 1,183 entries; `extract_zarc_v2.py` recovers all. First run's 125 partial-last-block errors were corrected; second manifest: 125 `ok`, 1,058 `skipped_existing`. SQLite comparison: all 1,183 present with matching declared sizes, **not a byte-for-byte integrity verification**. Manifest resource sizes sum to 1,115,053,569 bytes (~1,063.39 MiB).
- **TOER catalog:** `1009_FB41681A91008172.bin`, 50,237 records: type 0 = 4,481 unnamed `.bin`/`.anp`/`.clt`; type 1 = 33,508 `.tim`; type 2 = 12,248 `.pmd`. 45,756 grouped type-1/type-2 entries. The catalog's 64-bit filename hashes and ZARC resource hashes are distinct namespaces; observed hash search did not yield a catalog-to-resource mapping.
- **32-bit grouped `resource_id`:** `(group << 24) | (type << 16) | group_index`. Group and type bits matched all **45,756/45,756** grouped records. Across each group, the low 16-bit indices cover `0..N-1` without duplicates or gaps *across types combined*. This is a **logical catalog index**, not a proven physical archive offset.

| Group | Entries | Group index range |
|---:|---:|---:|
| 1 | 14,531 | 0–14,530 |
| 2 | 16,228 | 0–16,227 |
| 3 | 102 | 0–101 |
| 4 | 12,314 | 0–12,313 |
| 5 | 1,011 | 0–1,010 |
| 6 | 158 | 0–157 |
| 7 | 777 | 0–776 |
| 8 | 635 | 0–634 |

- **Numbered containers:** 891 validated numbered layouts in current full scan, kinds 3..7. 890 have section 0 with a valid indexed section; the exceptional `1136_FED18641A1E8BCE2.bin` has six direct `0x03` sections and no indexed section. The earlier `890` figure described **indexed** containers, not the entire numbered family.
- **Section inventory:** In 891 containers, `stage1_records.json` classifies **890 indexed section candidates**, **3,551 direct `0x03` sections**, **7 unclassified sections** (in `0168`, `0189`, `0409`, `0736`). The `0736` last section contains significant unparsed data; do not label it padding or empty.
- **Nested indexed sections:** `nested_index_audit.json` validated 890/890 index tables (no malformed or missing), with **890 first entries classified as 16-bit identifier tables** and **10,379 nested `0x03` records**. Entries use a count, relative offsets, an initial `u16` table, then framed records; index-count includes the initial identifier-table entry. The identification of this table as an ID lookup is strongly supported by the crosswalk, but its semantic relationship to TOER catalog IDs remains unverified.
- **`0x03` wrapper:** `03`, LE32 stored size, LE32 expected decoded size, then `stored` encoded bytes, then 0–3 zero alignment bytes. `0x03` is a *record marker*, **not a confirmed codec name**.
- **Deduplication:** SHA-256 over the encoded payload bytes (not wrappers) of all **13,930 records** (= 10,379 nested + 3,551 direct): **3,933 unique**; 536 groups with duplicates, 10,533 records in duplicated groups, **9,997 redundant copies**; zero validation failures. Nested: 650 unique among 10,379; direct sections: 3,283 unique among 3,551. These two category-level unique counts sum to 3,933 in this dataset (no cross-category hash overlap).
- **Identifier crosswalk:** Joining each nested record to its same-position 16-bit identifier gives **10,379/10,379** matches; **647 distinct identifiers** and **654 identifier/payload pairs**. **640** IDs always map to one SHA-256 payload; **IDs 1–7** each map to two variants. Their unusual alternatives reportedly cluster within the same **17 containers**; verify from complete records before building version logic. This is an ID-to-*nested-payload* relation; **not** an established filename-to-ZARC bridge.
- **Repeated common payloads:** nested position 1: 890 observations, 2 distinct payloads, largest cluster 873; position 8: 884 observations, 19 distinct payloads, largest cluster 755. Many early indexed records are shared boilerplate-like data across different containers. Do not equate 13,930 record instances with 13,930 unique assets.

## Open blockers — priority order

1. **Inner `0x03` decoder unimplemented.** Standard zlib/gzip/raw-deflate and tested LZMA representations were unsuccessful on representative inputs; this is not proof of a custom codec. No confirmed compressed-input/decompressed-output pair has been captured. **Do not conflate with outer ZARC LZMA.**
2. **TOER path → storage mapping unknown.** `TOE/Char/Main/Rid_01.tim` is catalog group 1, type 1, index 0 (`0x01010000`, filename hash `E2D6121BB0C5B351`). No verified link from this catalog tuple to a particular ZARC numbered container or decoded asset.
3. Seven unclassified sections; other data outside numbered family not fully understood; no regression across multiple game builds.

## Reverse-engineering dead ends / avoid repeating

- `GameNative.dll` `FUN_1802740f0 → FUN_180274810 → FUN_180276840 → FUN_180274cc0` is **outer archive LZMA-Alone**, used with `ZArcThreadMutex`. A prior memory hardware watchpoint landed in this chain, not in an inner decoder.
- Brute-force standard compression variations and searching for identical encoded prefixes did not locate the inner decoder. Shared payloads naturally explain many prefix hits.
- Found six MIPS/PSP ELF/PRX-looking resources associated with media libraries/drivers, not a verified inner decoder.
- Broad disassembly scans yielded candidate parser functions but no validated `0x03` consumer. Do not spend another session repeating unspecific scans.
- Proton/CachyOS is **not a blocker for offline extraction**; it can complicate native Windows debugging. Windows with x64dbg may help but is not guaranteed to solve it. Do not demand an OS switch without a narrow test.

## Recommended one-step next experiment

**Find the actual runtime consumer of the nine-byte `0x03` wrapper and capture one paired input/output buffer.** Prefer a targeted breakpoint/watchpoint **on an identified nested or direct `0x03` buffer used at runtime**, then identify its decoded-output buffer and verify `len(decoded) == expected` from the wrapper; retain a short binary signature or derived properties, not proprietary bytes in a public repository. Once this is established, implement a minimal decoder test and then correlate the output with a known `.tim` header and the catalog. A meaningful milestone is **one correctly decoded and named `Rid_01.tim`** (or a confirmed decoded record demonstrably linked to another asset). Do not resume record-count/SQL-audit loops unless they directly test a mapping hypothesis.

## User workspace (CachyOS, fish shell)

- Extracted resources: `~/zarc_extracted/`; names like `0008_E03CFF728B456990.bin`.
- Research DB: `~/TOER_research/database/toer_research.sqlite`. `resource` has `filename`, `size_bytes`, `path`; `zarc_manifest` has `resource_size`, `run_number`, `status`. Avoid `r.size` (nonexistent).
- Audit reports: `~/TOER_research/reports/stage1_records.json`, `nested_index_audit.json`, `payload_dedup_audit.json`.
- Optional encoded export folder: `~/TOER_research/encoded_records/`. Exports are **not decoded assets**.
- Example scripts: `toer_record_stage1.py`, `toer_nested_index_audit.py`, `toer_payload_dedup_audit.py`, `toer_make_id_crosswalk.py`, `toer_import_manifests_catalog.py`, `toer_build_research_db.py`. These were produced during investigation; check source/version and CLI before relying on them.
- Research crosswalk CSV: `identifier_payload_crosswalk.csv` / `toer_identifier_payload_crosswalk.csv` (654 unique ID/payload combinations). Reports are derived from user's specific extraction, not universally portable.
- The game has run under Steam/Proton. `GameNative.dll` can be inspected in Ghidra. Do not assume past runtime PIDs, module base addresses, or cache addresses remain valid.
- **Shell:** fish; Bash heredoc `python - <<'PY'` does not work natively. Use `.py`, `python -c`, or invoke `bash -c` deliberately.

## Evidence and confidence policy

Numerical counts above are from supplied `stage1_records.json`, `nested_index_audit.json`, and `payload_dedup_audit.json`, the catalog and database query outputs. SHA-256 is calculated over **encoded payload bytes**. Distinguish measured findings from interpretations. Exact meanings of section IDs and game-level asset placement are still unknown. No promise of completion time or percentage should be offered.
