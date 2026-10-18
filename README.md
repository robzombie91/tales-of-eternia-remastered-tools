# Tales of Eternia Remastered — Archive Tools & Format Research

Community reverse-engineering notes and **read-only extraction tools** for the PC release of *Tales of Eternia Remastered*.

> **Project status: experimental.** ZARC v2 extraction works against one tested PC game archive; the master `TOER` catalog parser is validated; nested resource decoding, linking catalog names to payloads, and repacking remain unsolved. This project is unofficial and is not affiliated with or endorsed by the game's publisher or developers.

## What works today

- Parse the observed `ZARC` **version 2** archive format.
- Extract resources from `Tales of Eternia Remastered_Data/StreamingAssets/Archive/DATA.zarc`.
- Decode **LZMA-Alone** compressed blocks and handle blocks stored without compression.
- Handle **65,536-byte logical blocks**, **128-byte resource alignment**, and partially used final blocks.
- Check archive boundaries and decompressed output lengths.
- Export resources using their 64-bit archive identifiers and create a JSON manifest.
- Leave the game installation and original archive unchanged.

**Tested result:** 1,183 of 1,183 indexed resources extracted successfully from one `DATA.zarc` file (916,771,200 bytes), across an initial and corrected extraction run. Testing against other game builds or archives has not yet been done.

## Repository layout

Suggested layout as the project grows:

```text
.
├── README.md
├── extract_zarc_v2.py       # Read-only ZARC extractor
├── docs/
│   ├── zarc-format.md       # Planned: detailed ZARC specification
│   └── toer-notes.md        # Planned: TOER reverse-engineering notes
└── .gitignore
```

Only add files to this tree when you have created them. The documentation files above are **planned**, not required to use the extractor.

## Requirements

- **Python 3** with the standard library (`lzma`, `struct`, etc.); no `pip` dependencies.
- A legally obtained PC installation of *Tales of Eternia Remastered*.
- Disk space for the extracted resources.

Developed and tested on **CachyOS Linux**. The Python extractor should also be portable to other operating systems that provide the standard `lzma` module, though those environments have not been tested.

## Usage

From the `Tales of Eternia Remastered_Data` directory:

### Extract five resources as a test

```bash
python extract_zarc_v2.py StreamingAssets/Archive/DATA.zarc --output ~/zarc_extracted --limit 5
```

### Extract all resources

```bash
python extract_zarc_v2.py StreamingAssets/Archive/DATA.zarc --output ~/zarc_extracted
```

Or supply absolute paths for both the archive and output directory:

```bash
python extract_zarc_v2.py "/path/to/Tales of Eternia Remastered_Data/StreamingAssets/Archive/DATA.zarc" --output "/path/to/output"
```

Output names look like:

```text
0000_E001331793365D5B.bin
0001_E00173BDC66D2B36.bin
...
manifest_v2.json
```

The hexadecimal suffix is an **archive lookup identifier**, **not** the original game asset filename. The extractor preserves existing output files instead of overwriting them. **Important:** skipped files are not checksum-verified; a preexisting, damaged output file may be skipped. If a complete re-extraction is needed, use a *new empty output directory*. If `manifest_v2.json` already exists, the script preserves it rather than replacing it.

### Command-line options

```text
archive            Path to DATA.zarc (required)
-o, --output DIR   Extraction destination (default: ~/zarc_extracted)
--limit N          Extract the first N archive entries only
```

## ZARC v2: observed format

The following layout was established using Ghidra analysis of `GameNative.dll` and checked against a real archive using Python. It is a **working description of the tested archive**, not an official or complete specification.

| Header offset | Size | Observed meaning / value |
| --- | ---: | --- |
| `0x00` | 4 | ASCII `ZARC` |
| `0x04` | 4 | Version: `2` |
| `0x08` | 4 | End of metadata region: `63,738` |
| `0x0C` | 4 | Index record stride: `24` bytes |
| `0x10` | 4 | Index record count: `1,183` |
| `0x14` | 4 | Unknown (`2,000` in tested archive) |
| `0x18` | 4 | Unknown (`1` in tested archive) |
| `0x1C` | 4 | Logical block size: `65,536` bytes |
| `0x20` | 4 | Stored resource alignment: `128` bytes |
| `0x24` | 4 | Unknown (`1` in tested archive) |

Header numeric fields are **big-endian**. The header is **40 bytes** (`0x28`).

### Index records

Immediately after the header are fixed-size **24-byte records**:

| Record bytes | Size | Interpretation |
| --- | ---: | --- |
| `0–7` | 8 | Resource identifier / lookup key, big-endian |
| `8–12` | 5 | Logical (uncompressed) resource size, big-endian |
| `13–16` | 4 | Unknown metadata field |
| `17–19` | 3 | Index of the resource's first logical block |
| `20–23` | 4 | Absolute archive offset in 128-byte units |

For the tested archive:

- The index starts at `0x28` and ends at `0x6F10`.
- A **two-byte, big-endian block-length table** follows the index.
- A zero in that table indicates a full-size stored block (`65,536` bytes); other entries give the stored length of a compressed block.
- Resources start at 128-byte-aligned archive offsets. The first begins at `0xF900`.
- The number of logical blocks per resource is `ceil(uncompressed_size / 65536)`.
- The recorded start of every successive resource agrees with the preceding resource's stored block sizes rounded to 128-byte alignment (**1,182 / 1,182 checks**).
- Compressed blocks tested so far use Python-compatible **LZMA-Alone** streams.
- Final logical blocks may decode to 65,536 bytes even when the resource's declared size requires fewer; the extractor trims only the excess at the **end of the resource**.

These points describe the observed archive and may require revision for other versions.

## Research findings: formats inside ZARC

Extraction reveals a mix of recognizable and proprietary resources. An initial `file` scan of the 1,183 extracted files reported:

| Count | `file` identification | Notes |
| ---: | --- | --- |
| 948 | `data` | Unidentified or proprietary binary data |
| 110 | RIFF/WAVE stereo, 44.1 kHz | Audio assets |
| 102 | `GLS_BINARY_LSB_FIRST` | Unverified identification; needs further analysis |
| 17 | Tar archive with `PSMF0012` string | Likely PSP PSMF movie data; verify container layout |
| 2 | 32-bit MIPS ELF | PSP-style PRX modules identified below |
| 2 | GTA audio index (SDT) | Unverified `file` identification |
| 1 | DitPack archive | Unverified `file` identification |
| 1 | Atari DEGAS bitmap | Likely a false positive |

The two ELF modules expose the names **`sceMpeg_library`** and **`sceATRAC3plus_Library`** in their `.rodata.sceModuleInfo` sections. Their presence **does not by itself establish** that the PC version executes PSP code or uses a full PSP emulator.

### Master `TOER` catalog (parsed and verified)

`1009_FB41681A91008172.bin` has a **50,237-record** catalog of identifiers, filenames, resource types and validated custom 64-bit filename hashes. `export_toer_catalog.py` exported all 50,237 rows (zero validation errors). The catalog is **not** an extractor for the individual texture/model payload bytes. See `TOER_FORMAT.md` and `TOER_RESEARCH_CHECKPOINT.md` for details.

### Numbered containers (inner codec unsolved)

890 extracted resources passed common numbered-container framing checks. **10,379** `0x03` nested records were validated with 9-byte length wrappers and four-byte zero padding; their encoding algorithm and linkage to `.tim`/`.pmd` catalog names remain unknown. See `NUMBERED_CONTAINERS.md`.

### Native investigation

Ghidra analysis of `GameNative.dll` confirmed the **outer ZARC LZMA-Alone** path, not the nested resource decoder. See `ZARC_FORMAT.md` for function addresses and evidence. Managed `Assembly-CSharp.dll` uses Unity Addressables and exposes `UgxAssetManager.LoadAsset<T>(uint)`; whether it processes the numbered containers is unverified.

## Roadmap

- [x] Decode and validate the tested ZARC v2 header and index.
- [x] Extract all 1,183 ZARC entries with no reported extraction failures.
- [x] Identify LZMA-Alone compression and raw block handling.
- [x] Record the observed ZARC v2 layout for the tested archive (not other builds).
- [x] Decode and export the 50,237-record master `TOER` catalog and validate filename hashes.
- [x] Document validated framing for 10,379 nested `0x03` records.
- [ ] Identify inner `0x03` codec and extract at least one verified payload.
- [ ] Recover and match original filenames to extracted content.
- [ ] Identify internal texture, model, text, and script formats.
- [ ] Add automated tests using synthetic fixtures (not copyrighted assets).
- [ ] Investigate asset replacement/repacking, **only after** read-only formats are understood.

## Contributing

Issues, tested corrections, documentation, small synthetic samples, and portable tooling are welcome. Please include the game build, OS, commands used, and reproducible results when reporting a format difference.

**Do not upload or commit copyrighted game archives, extracted assets, executables, or proprietary DLLs.** Instead, share offsets, format descriptions, code snippets, and hashes or small hand-created test fixtures where appropriate.

## Legal / disclaimer

This is an independent interoperability, archival research, and modding project. It is **not affiliated with or endorsed by** the game's rights holders. All trademarks and game content belong to their respective owners. You are responsible for complying with applicable laws, licenses, and the game's terms. The repository should distribute **tools and documentation only**, not copyrighted game data.

## License

**Choose a license before publishing.** MIT is a practical option for a small Python utility, but only add an MIT `LICENSE` file if you intend to license your own code under those terms. This README does not itself grant a license to third-party game data.
