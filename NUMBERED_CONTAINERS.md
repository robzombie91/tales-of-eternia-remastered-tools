# Numbered resource containers — research checkpoint (2026-10-18)

**Status: framing verified on the tested extraction; the inner codec and mapping to catalog names are NOT solved.** All samples are extracted files under `~/zarc_extracted`, never the game installation.

## Outer container layout

A survey found 896 resources whose first LE uint32 is `kind` in 3–7, of which **890 passed the common container-layout checks**. At file offset `0x04`, the second LE uint32 equals `4 * (kind + 1)` (thus kinds 3..7 have headers of 16,20,24,28,32 bytes). Following are `kind-1` LE uint32 section offsets from `0x08`; the initial section runs from `header_size` to the first section offset. This is an observed family structure, not a fully specified format; retain the anomalous cases.

The initial section is an indexed-record region: LE uint32 record count, followed by that many LE uint32 offsets relative to the section start. The first offset is normally `4 + 4 * count`. First indexed record has a first byte of `0x01`; subsequent indexed records begin with `0x03`. There were **11,269 indexed records** across the 890 validated files, with only **1,135 unique SHA-256 record byte strings**, indicating substantial reuse; do not assume those records are all individually useful graphical assets.

## `0x03` nested wrapper

**Validated across 10,379 records, zero framing exceptions** with exact stored counts and 0–3 trailing zero pad bytes to 4-byte alignment:

| Relative offset | Size | Meaning |
|---|---:|---|
| `+0x00` | 1 | marker `0x03` |
| `+0x01` | 4 | LE uint32 stored payload byte count |
| `+0x05` | 4 | LE uint32 expected output byte count |
| `+0x09` | N | encoded payload, N = stored byte count |
| after payload | 0–3 | zero alignment pad |

`0x03` is a **record marker**, not a proven codec identifier. The actual algorithm remains unknown. Standard zlib/gzip/deflate, LZMA-Alone and tried raw LZMA1 settings did not decode a representative payload; this excludes only those *tested representations and parameters*, not every possible variant. The native ZARC LZMA-Alone decoder is separately identified and belongs to the **outer archive**.

Across 10,379 records, the first eight bytes of encoded payload exhibited 15 distinct values, heavily skewed by identical repeated records. Top frequencies: `d5 10 ec f0 08 ec f0 8c` 6,493; `d5 10 ec f0 08 ec f0 2c` 2,483; `d5 10 ec f0 08 ec f0 4c` 1,085 (96.9% total). These repetitions are not independent proof of a special codec.

## Oversized sample and corrected interpretation

`0736_F43C42C59BEBA767.bin` has length **179,908,608 bytes**. Its last section begins at **`0x3F790`**, size **179,648,624 bytes**. The section starts `03 5a 1c 00 00 78 42 00 00 ...`: interpreted as one framed entry, **stored=7,258**, **expected output=17,016**, consuming **7,267 bytes before four-byte alignment** (7,268 after alignment). The byte immediately following that aligned entry and a nearby interval are zero, so a naive loop expecting back-to-back `0x03` records stops after one entry.

**Important correction:** This does NOT mean the rest is padding. A full-section scan counted **174,235,097 nonzero bytes, or 96.99%**. Its first and last MiB had entropy ~7.809 and ~7.765 bits/byte. A 1 MiB-granularity scan reported active blocks spanning the whole section; it cannot detect small internal gaps. The organization of the rest of this huge section is **unresolved**. Do not call it one continuous compressed record or mostly empty.

## Next viable research direction

1. Locate the **consumer of the nine-byte marker/length/length wrapper**, not the already-solved ZARC LZMA decoder. A runtime debugger under Proton is one option, but has not been configured or run.
2. Capture an actual decoded record and verify its size equals `expected output`, then identify its transformation and relation to catalog names. Avoid assertions about codecs based on shared prefixes.
3. Automate the evidence-based parser after confirming the decoded format; preserve anomalies and bounds checks.

## Environment

CachyOS Linux; user shell is **fish** (Bash `python - <<'PY'` heredocs fail in fish; use `python -c '...'`, a saved `.py` script, or explicitly enter Bash). `GameNative.dll` holds native archive code; `Assembly-CSharp.dll` contains `UgxAssetManager.LoadAsset<T>(uint addressableId)` and Unity `AsyncOperationHandle<T>` use. This indicates a managed Addressables layer but does **not** establish the numbered containers are managed in C#.

## Full inventory correction / addendum — October 18, 2026

This addendum supersedes earlier broad references to **890 containers** or **11,269 indexed records** as if each were a compressed asset. There are **891** structurally recognized numbered containers in the current scan, **890** with indexed section zero, and one (`1136_FED18641A1E8BCE2.bin`) with all six sections directly framed. The **11,269 indexed entries** consist of exactly **890 initial identifier tables + 10,379 nested `0x03` records**. There are also **3,551 direct-section `0x03` records** and **7 unclassified sections** in four containers (`0168`, `0189`, `0409`, `0736`). The 0736 anomaly remains nonempty and unresolved.

`toer_nested_index_audit.py` found 0 malformed indexed tables or missing source files. Initial entries are candidate `u16` identifier tables of one identifier per following record. The `toer_payload_dedup_audit.py` SHA-256 audit over **encoded payload bytes** found **13,930 occurrences, 3,933 distinct**, 9,997 redundant occurrences. Indexed/nested = 10,379 instances / 650 distinct; direct = 3,551 / 3,283. **All 10,379 nested records** crosswalk to identifiers; **647 IDs** and **654 ID/SHA combinations**; IDs 1–7 have two variants, and every other identifier observed has one. This is strong evidence of a nested-record content-ID mechanism, not proven linkage to the `.tim`/`.pmd` catalog IDs. Refer to `TAKEOVER_HANDOFF.md` for samples, source artifact locations, and blockers.

**Warning:** prior statements that all first indexed records begin with byte `0x01` are structural observations about the table and must not be mistaken for a proven record codec. The `0x03` wrapper and its decoding algorithm remain separate questions. Older discussions of 10,379 nested records should also be updated to include the newly characterized 3,551 direct sections.
