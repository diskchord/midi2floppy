# midi2floppy
A command-line utility that **recursively discovers MIDI files, renames them to strict 8·3 filenames, buckets them into ≤ 60-file / ≤ 600 KB groups, assembles those groups into exact 720 KB FAT12 images, and converts those images to HFE**—ready for Greaseweazle-style floppy-drive emulators.

> **About the code**  
> The initial scaffolding and refactor outline were produced with assistance from **OpenAI ChatGPT o3**. All logic, testing, and documentation were subsequently reviewed and refined by the maintainer.

---

## ✨ Features

| Capability | Notes |
|------------|-------|
| **Recursive ingest** | Point to any root directory; all sub-folders are processed. |
| **Smart bucketing** | Guarantees every disk holds ≤ 600 KB of data *and* ≤ 60 files (well within FAT12 limits). |
| **Exact images** | Uses `mformat` + `mcopy` to create authentic 720 KB (737 280-byte) FAT12 layouts. |
| **HFE output** | Calls `gw convert --format ibm.720` to emit `*.hfe` images for flash-floppy emulators. |
| **Deterministic names** | Sequential `DSKA0000.img/.hfe`, `DSKA0001…`; a `directory_map.txt` tracks source ↔ image mapping. |

---

## 🔧 Requirements

| Tool | Purpose | Tested With |
|------|---------|------------|
| Python ≥ 3.8 | Runtime | 3.11 |
| **mtools** (`mformat`, `mcopy`) | FAT12 image creation | 4.0.43 |
| **Greaseweazle CLI** (`gw`) | IMG → HFE conversion | 0.39 |

All executables must be available in your **`$PATH`**.

---

## 🚀 Installation

```bash
git clone https://github.com/<your-org>/midi-to-hfe.git
cd midi-to-hfe
# no external Python deps; stdlib only
