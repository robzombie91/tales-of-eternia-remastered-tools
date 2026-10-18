# TOER Format — Research Notes (Unsolved)

**Status:** early, experimental reverse engineering. No reliable TOER parser or asset-name mapping has been established. **Do not treat speculative fields below as a definitive format specification.**

## Observed sample

- Extracted ZARC entry: `1009_FB41681A91008172.bin` (archive identifier `FB41681A91008172`).
- File size: **5,411,080 bytes**.
- Signature at `0x00`: ASCII **`TOER`** (`54 4F 45 52`).
- The sample includes many original-style `TOE/` paths and `TOE_upscale/` references.
- A `strings -a | grep -E '^TOE/|^TOE_upscale/' | sort -u | wc -l` experiment returned **44,211 distinct candidate path strings**. This does **not** establish that 44,211 separate assets exist or that all strings map to ZARC entries.

Some observed strings:

```text
TOE/Char/Main/Rid_01.tim
TOE/Char/Main/Rid_01_plt_01_00.tim
TOE/Char/Main/Far_01.tim
TOE/Char/Main/Keel_01.tim
TOE/Char/Main/Mer_01.tim
TOE/Char/Main/Quickie.tim
TOE/btl/bin/bt_m001.bin
TOE/btlmap/magic/ef001.tim
TOE_upscale/
```

These strongly suggest resource name strings for character textures, battle assets and possibly enhanced assets. The target asset data and exact name-to-record mapping remain unknown.

## Beginning of file

First 40 bytes, with 64-bit LE offset candidates apparent at `0x18`:

```text
00000000  54 4F 45 52 00 00 00 00 01 00 00 00 02 00 00 00
00000010  3D C4 00 00 00 00 00 00 98 57 0C 00 00 00 00 00
00000020  A8 60 0C 00 00 00 00 00 ...
```

| File offset | Little-endian value | Status |
| --- | --- | --- |
| `0x00` | `TOER` | Verified four-byte magic |
| `0x04` | `0` (32-bit) | Unknown |
| `0x08` | `1` (32-bit) | Possible version, **unconfirmed** |
| `0x0C` | `2` (32-bit) | Unknown |
| `0x10` | `50,237` (`0xC43D`, 32-bit) | Unknown count/size field |
| `0x18` | `0xC5798` (64-bit LE) | Candidate pointer/offset |
| `0x20` | `0xC60A8` (64-bit LE) | Candidate pointer/offset |
| `0x28` | `0xCB5D0` (64-bit LE) | Candidate pointer/offset |
| `0x30` | `0xCBA08` (64-bit LE) | Candidate pointer/offset |

**Offset scan:** Reading 64-bit little-endian values from `0x18` showed **4,481 consecutive increasing in-bounds values**; the monotonic sequence stopped at offset `0x8C20`, where the next value decreased to `0xC43E8`. The last preceding value was `0x291DD8`. This finding **does not** prove that there are exactly 4,481 entries: the next value is still in bounds and could begin another logical group.

Early tests accidentally stopped at `0x1000`, incorrectly suggesting a table length of 509. That was an artificial scan limit, **not a finding about the file format**.

## Data at candidate offsets

The three sampled offsets point to bytes with repeated structural patterns, but nothing has yet identified their field meanings:

```text
0x0C5798: 7E 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 DA F2 2A 00 ...
0x0C60A8: B8 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 DA F2 2A 00 ...
0x0CB5D0: D9 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 DA F2 2A 00 ...
```

The recurring `DA F2 2A 00` sequence could represent the little-endian integer `0x002AF2DA`, but it has **not** been proven to be a pointer.

At file offset `0x2AF2DA`, examination found a NUL byte immediately before sequential, NUL-terminated ASCII strings:

```text
0x0101007E
0x0101007F
0x01010080
0x01010081
...
```

The string `0x0101007E` starts at `0x2AF2DB`. These appear to be text identifiers, **not** actual resource payload offsets. Their relationship to the preceding candidate records remains unknown.

## Related ZARC and PSP findings

The parent `DATA.zarc` contains **1,183 ZARC entries**; those are *not* equivalent to the 44,211 candidate paths inside this single TOER file. A separate survey of extracted files found WAV audio, candidate `PSMF0012` PSP movie files, and two PSP-style MIPS PRX modules bearing `.rodata.sceModuleInfo` names `sceMpeg_library` and `sceATRAC3plus_Library`. Those discoveries provide historical context **but do not prove** the PC release runs an emulator or that TOER itself stores those file types.

## Next reproducible investigations

1. Determine whether the values beginning at `0x18` are one or several tables. Examine the transition around `0x8C20` and correlate candidate offsets with record boundaries.
2. Identify individual TOER record widths and test whether pointer-like fields refer to string starts, index records, or data regions. Prefer testing several records rather than drawing conclusions from one.
3. Identify where the `TOE/` path string pool begins/ends, and what references it. The sample path `TOE/Char/Main/Rid_01.tim` was observed at string offset `0x329B85`.
4. Compare structured counts against header value `50,237` (`0xC43D`) without assuming it is a record count.
5. Build a read-only TOER listing tool **only after** multiple record-to-name references validate consistently. Avoid dumping embedded copyrighted data to the repository.

### A safe inspection command (fish-compatible)

```fish
python -c '
from pathlib import Path
p = Path.home() / "zarc_extracted/1009_FB41681A91008172.bin"
d = p.read_bytes()
for offset in range(0x8BE0, 0x8C80, 8):
    print(hex(offset), hex(int.from_bytes(d[offset:offset+8], "little")))
'
```

## Research quality and distribution

Label new observations **verified**, **inferred**, or **hypothesis**. Include the precise byte offset, value, parsing rule, and at least one repeatable test; mention counterexamples. Keep original game files and extracted assets out of Git repositories. See `ZARC_FORMAT.md` for the solved outer archive format and `../AGENTS.md` for contributor/agent guidance.
