# Agent Instructions — Tales of Eternia Remastered Tools

This repository contains **unofficial, read-only reverse-engineering tools and format notes** for the PC release of *Tales of Eternia Remastered*. Work from observed evidence, not assumptions. Read `README.md`, `docs/ZARC_FORMAT.md`, and `docs/TOER_FORMAT.md` before changing parsers.

## Priorities

1. Keep game installations and source archives untouched.
2. Maintain reliable ZARC v2 extraction and regression tests.
3. Research TOER structures and the relationship between internal asset paths and data records.
4. Improve documentation with reproducible evidence and clear confidence levels.
5. Do not introduce repacking or modification features without explicit scope and rigorous tests.

## Confirmed versus experimental

- **Validated on one PC `DATA.zarc`:** `ZARC` v2; 40-byte big-endian header; 24-byte index records; 2-byte big-endian block lengths; 64 KiB logical blocks; 128-byte resource alignment; LZMA-Alone and raw block handling; 1,183 of 1,183 files extracted successfully across two runs.
- **Confirmed in one extracted resource:** file `1009_FB41681A91008172.bin` begins with `TOER`, is 5,411,080 bytes, and contains numerous `TOE/` and `TOE_upscale/` path strings.
- **Not confirmed:** TOER record structures, interpretation of all TOER header fields, resource name-to-hash mappings, whether the PC game executes extracted PSP PRX code, or ZARC compatibility across other builds.
- A pattern or `file`-utility guess is **not** a proven format identification.

## Working conventions

- Target Python 3 with the standard library where practical; `lzma` is already used. Avoid dependencies unless there is a demonstrated reason.
- Keep parsers **read-only** regarding archives. Write outputs only to a user-selected destination.
- Validate bounds, counts, widths, alignment, and decoded lengths before allocating or writing large amounts of data.
- Treat input archives as untrusted. Avoid shell execution, path traversal, unchecked offsets, and unbounded decompression.
- Never overwrite existing extracted files by default; document that skipped files are **not** checksum-verified.
- Use temporary/partial outputs and delete them after failures. Preserve successful outputs when later entries fail.
- Maintain clear errors and nonzero exit codes on failures.
- Do not silently change output filenames, manifest formats, CLI flags, or compatibility behavior.
- Write automated tests with **hand-created synthetic archives/fixtures**, not redistributed game assets.
- Prefer small, independently verifiable patches, with regression cases for compressed blocks, raw blocks, padded final blocks, invalid metadata, and resume/skip logic.

## Documentation and evidence

When documenting a discovery, include: observed file/build (when known), exact offsets and byte order, a short hex/code example, the test performed, outcome, and whether the statement is **verified**, **inferred**, or **unknown**. Do not promote hypotheses to facts. Record corrections explicitly.

Relevant Ghidra functions observed during the original investigation (addresses are **build-specific**, not stable API):

- `GameNative.dll` `FUN_180272510`: archive opening and header/index loading.
- `FUN_18026f2b0`: decode 40-byte ZARC header.
- `FUN_18026f440`: decode 24-byte ZARC records.
- `FUN_18026ea00`: archive key lookup.
- `FUN_18026f570` / `FUN_18026f640`: custom CRC-based name hashing; mapping of actual path names to ZARC keys remains unresolved.

Consult `docs/ZARC_FORMAT.md` for byte layouts and `docs/TOER_FORMAT.md` for the current TOER research boundary.

## Legal and distribution boundaries

Do **not** commit or propose redistribution of original game archives, extracted copyrighted assets, executables, DLLs, game video/audio, or other proprietary data. Publish code, documentation, reproducible offsets, and synthetic samples only. Do not imply affiliation with the publisher or developers. Do not assert any license unless the repository owner has added it.

## Response style for collaborating agents

Explain complicated reverse-engineering steps in plain English. Prefer one focused next experiment with a measurable expected result. Correct prior misunderstandings directly; distinguish confidence from enthusiasm.
