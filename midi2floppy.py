#!/usr/bin/env python3
"""
midi2floppy.py
Copyright © 2025 Alexander Peppe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SECTOR_SIZE = 512
TOTAL_SECTORS = 1440
SYSTEM_SECTORS = 1 + 3 + 3 + 14  # boot + FAT1 + FAT2 + root dir
DATA_SECTORS = TOTAL_SECTORS - SYSTEM_SECTORS  # 1 419 clusters
MAX_CLUSTERS = DATA_SECTORS

MAX_PAYLOAD_BYTES = 600 * 1024            # 600 KB
MAX_FILES_PER_DISK = 60                   # stricter than FAT root limit (224)

VALID_EXTS = {'.fil', '.mid', '.midi'}
IMG_TEMPLATE = "DSKA{:04d}"
IMAGES_DIRNAME = "Images"
MAPPING_FILE = "directory_map.txt"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_shortname(filename: str) -> str:
    stem = Path(filename).stem
    letters = ''.join(c.upper() for c in stem if c.isalpha())
    if len(letters) < 6:
        letters += "DKSONG"
    return letters[:6]


def is_generated_dir(dirpath: Path, root: Path) -> bool:
    if dirpath == root / IMAGES_DIRNAME:
        return True
    par = dirpath.parent
    return par and dirpath.name.startswith(par.name + "_") and dirpath.name[len(par.name)+1:].isdigit()

# ---------------------------------------------------------------------------
# File ops
# ---------------------------------------------------------------------------

def rename_files(directory: Path) -> None:
    files = sorted([p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXTS],
                   key=lambda p: p.name.lower())
    for idx, path in enumerate(files):
        short = get_shortname(path.name)
        if idx > 99:  # maintain 8.3
            short = short[:5]
        ext = '.FIL' if path.suffix.lower() == '.fil' else '.MID'
        new_name = f"{idx:02d}{short}{ext}"
        new_path = path.with_name(new_name)
        if path != new_path:
            print(f"Renaming {path.relative_to(directory)} → {new_name}")
            path.rename(new_path)

# ---------------------------------------------------------------------------
# Bucketing
# ---------------------------------------------------------------------------

def rounded_clusters(size: int) -> int:
    return (size + SECTOR_SIZE - 1) // SECTOR_SIZE or 1


def bucket_files(directory: Path) -> list[Path]:
    base = directory.name
    files = sorted([p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXTS],
                   key=lambda p: p.name.lower())
    if not files:
        return []

    buckets: list[Path] = []
    bucket_idx = 1
    used_clusters = used_bytes = file_count = 0
    bucket_dir = directory / f"{base}_{bucket_idx}"
    bucket_dir.mkdir(exist_ok=True)
    buckets.append(bucket_dir)

    for f in files:
        size = f.stat().st_size
        clusters = rounded_clusters(size)

        needs_new_bucket = (
            used_clusters + clusters > MAX_CLUSTERS or
            used_bytes + size > MAX_PAYLOAD_BYTES or
            file_count + 1 > MAX_FILES_PER_DISK
        )

        if needs_new_bucket:
            bucket_idx += 1
            bucket_dir = directory / f"{base}_{bucket_idx}"
            bucket_dir.mkdir(exist_ok=True)
            buckets.append(bucket_dir)
            used_clusters = used_bytes = file_count = 0

        shutil.move(str(f), bucket_dir / f.name)
        used_clusters += clusters
        used_bytes += size
        file_count += 1
    return buckets

# ---------------------------------------------------------------------------
# Image creation & conversion
# ---------------------------------------------------------------------------

def build_image(bucket: Path, img_path: Path) -> None:
    subprocess.run(["mformat", "-f", "720", "-C", "-i", str(img_path), "::"], check=True)
    for f in bucket.iterdir():
        if f.is_file():
            subprocess.run(["mcopy", "-i", str(img_path), str(f), "::"], check=True)


def convert_to_hfe(img_path: Path, hfe_path: Path) -> None:
    subprocess.run(["gw", "convert", "--format", "ibm.720", str(img_path), str(hfe_path)], check=True)

# ---------------------------------------------------------------------------
# Recursion driver
# ---------------------------------------------------------------------------

def process_directory(directory: Path, root: Path, images_dir: Path,
                       counter: list[int], mapping: dict[str, list[str]]):
    if is_generated_dir(directory, root):
        return

    rename_files(directory)
    for bucket in bucket_files(directory):
        idx = counter[0]; counter[0] += 1
        base = IMG_TEMPLATE.format(idx)
        img = images_dir / f"{base}.img"
        hfe = images_dir / f"{base}.hfe"
        print(f"Building {img.name} from {bucket.relative_to(root)} …")
        build_image(bucket, img)
        convert_to_hfe(img, hfe)
        mapping[str(directory.relative_to(root))].append(hfe.name)

    for child in directory.iterdir():
        if child.is_dir():
            process_directory(child, root, images_dir, counter, mapping)

# ---------------------------------------------------------------------------
# Entry‑point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="600 KB/60‑file IMG‑HFE packager")
    ap.add_argument("directory", help="Root directory to process")
    root = Path(ap.parse_args().directory).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"Error: {root} is not a directory")

    images_dir = root / IMAGES_DIRNAME
    images_dir.mkdir(exist_ok=True)

    counter = [0]
    mapping: dict[str, list[str]] = defaultdict(list)
    process_directory(root, root, images_dir, counter, mapping)

    with (images_dir / MAPPING_FILE).open("w", encoding="utf-8") as fp:
        for folder, hfes in mapping.items():
            fp.write(f"{folder} > {', '.join(hfes)}\n")
    print(f"Created {counter[0]} images (≤600 KB & ≤60 files each). Mapping saved.")


if __name__ == "__main__":
    main()

