#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Joshua Kimsey
"""Regenerate the color-scheme tables in the docs.

The README and ``docs/web-integration-guide.md`` each embed a color-scheme
table between a pair of marker comments:

    <!-- BEGIN GENERATED: {region} -->
    ...generated content...
    <!-- END GENERATED: {region} -->

This script regenerates exactly the text between the markers (everything
outside is preserved byte-for-byte) so the tables stop being hand-maintained.

Regions:

  * ``color-scheme-table``              -- README.md (``| ID | Name |`` table)
  * ``color-scheme-table-descriptions`` -- docs/web-integration-guide.md
    (``| ID | Name | Description |`` table)

Run without arguments to rewrite the tables in place:

    python3 scripts/generate_scheme_docs.py

Run with ``--check`` to verify every region is up to date, that no doc or
example still carries a stale scheme-count string, and that the
``docs/color-schemes-preview.stamp`` fingerprint matches the current
preview-PNG inputs (the scheme list, color-table data, and rendering
script); it writes nothing and exits 1 if anything is out of date:

    python3 scripts/generate_scheme_docs.py --check
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Pull the scheme list straight from the project -- adding a new scheme to
# ``SCHEME_NAMES`` propagates through automatically.
sys.path.insert(0, str(REPO_ROOT / "src"))
from librewxr.colors.schemes import SCHEME_NAMES  # noqa: E402

# Preview-PNG staleness tracking. ``scripts/generate_color_scheme_previews.py``
# writes a fingerprint stamp of everything that shapes its PNGs; ``--check``
# compares the current inputs against that stamp so stale previews fail CI.
PREVIEW_SCRIPT = REPO_ROOT / "scripts" / "generate_color_scheme_previews.py"
STAMP_PATH = REPO_ROOT / "docs" / "color-schemes-preview.stamp"


# Verbatim descriptions, keyed by scheme ID (drawn from
# docs/web-integration-guide.md). ``255`` is the raw grayscale fallback.
DESCRIPTIONS = {
    0: "Grayscale intensity",
    1: "Classic Rain Viewer colors",
    2: "Blue-to-red gradient",
    3: "High-contrast scheme",
    4: "Matches TWC broadcast colors",
    5: "European-style colors",
    6: "US NWS standard radar colors",
    7: "Full rainbow gradient (recommended default — closest to standard weather radar)",
    8: "Muted, minimal style",
    9: "Discrete 5-dBZ stepped scale contributed by Valerio at Datameteo Educational; reads as distinct bins from drizzle through large hail / tornado",
    10: "High-resolution palette by Ben Mitchell (WxTools.org); cyan-blue through smooth greens into yellow / orange / red, with a magenta band at 55–60 dBZ and a grayscale tail for extreme reflectivity. Also used by RadarScope, Supercell Wx, and others",
    11: "Stepped 5-dBZ operational palette used by NOAA/NSSL's MRMS Product Viewer for composite reflectivity. Cyan through blue / green / yellow / orange / red into a magenta band at 70 dBZ, with light-tan and purple swatches for sub-zero / clear-air returns",
    12: "Stepped 5-dBZ palette designed by ABC 33/40 Chief Meteorologist James Aydelott, published via Ben Mitchell's WxTools (WxTools.org). Green ramp for light precip (10–30 dBZ) stepping through yellow / orange / red for moderate-to-heavy, into a pink / magenta convective band at 55+ dBZ. Snow variant reuses the Universal Blue gradient. Also used by RadarScope, Supercell Wx, and others",
    13: "MetService New Zealand-inspired palette (dark-basemap variant), contributed by ashuttl via GitHub discussion #4",
    14: "Radar palette inspired by the iOS Windy app, contributed by Gerrit Grunwald (Photo-Planner); gray for light precipitation deepening through blue / teal / green / yellow / orange into deep purple for extreme reflectivity",
    255: "Grayscale proportional to dBZ — useful for custom client-side coloring",
}


def compute_preview_fingerprint(preview_script: Path) -> str:
    """Fingerprint the inputs that determine the preview PNG output.

    Hashes the scheme list, the color-table data, the LUT-defining module,
    and the preview-rendering script itself, so any change that would alter
    the rendered PNGs invalidates the stamp. Must stay importable without
    matplotlib (it only needs librewxr.colors.schemes, i.e. numpy).
    """
    hasher = hashlib.sha256()
    hasher.update(b"librewxr-preview-fingerprint-v1\n")
    # 1. The scheme list (ID + display name), sorted for stability.
    for scheme_id, name in sorted(SCHEME_NAMES.items()):
        hasher.update(f"{scheme_id}\x00{name}\x00".encode("utf-8"))
    # 2. The LUT-defining module (headers + parsing rules).
    hasher.update((REPO_ROOT / "src" / "librewxr" / "colors" / "schemes.py").read_bytes())
    # 3. The color-table data the LUTs are parsed from.
    hasher.update((REPO_ROOT / "src" / "librewxr" / "colors" / "color_table.csv").read_bytes())
    # 4. The preview-rendering script itself (axis ranges, layout, DPI...).
    hasher.update(preview_script.read_bytes())
    return hasher.hexdigest()


def _begin(region: str) -> str:
    return f"<!-- BEGIN GENERATED: {region} -->"


def _end(region: str) -> str:
    return f"<!-- END GENERATED: {region} -->"


def _strip(line: str) -> str:
    return line.rstrip()


def render_table(region: str) -> str:
    """The generated text body (without the surrounding marker lines)."""
    names = list(SCHEME_NAMES.items())
    if region == "color-scheme-table":
        lines = ["| ID | Name |", "|---|---|"]
        for scheme_id, name in names:
            lines.append(f"| {scheme_id} | {name} |")
        lines.append("| 255 | Raw (grayscale) |")
        return "\n".join(lines)
    if region == "color-scheme-table-descriptions":
        lines = ["| ID | Name | Description |", "|----|------|-------------|"]
        for scheme_id, name in names:
            lines.append(f"| {scheme_id} | {name} | {DESCRIPTIONS[scheme_id]} |")
        lines.append(f"| 255 | Raw | {DESCRIPTIONS[255]} |")
        return "\n".join(lines)
    raise ValueError(f"Unknown region: {region}")


# Target file per region.
REGION_FILES = {
    "color-scheme-table": REPO_ROOT / "README.md",
    "color-scheme-table-descriptions": REPO_ROOT / "docs" / "web-integration-guide.md",
}


def update_region(path: Path, region: str) -> bool:
    """Rewrite one region in ``path``; return True if the file changed."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    begin_marker = _begin(region)
    end_marker = _end(region)
    begin_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if _strip(line) == begin_marker:
            if begin_idx is not None:
                raise SystemExit(
                    f"{path}: duplicate BEGIN marker for region '{region}' (line {i + 1})"
                )
            begin_idx = i
        if _strip(line) == end_marker:
            if end_idx is not None:
                raise SystemExit(
                    f"{path}: duplicate END marker for region '{region}' (line {i + 1})"
                )
            end_idx = i
    if begin_idx is None:
        raise SystemExit(f"{path}: missing BEGIN marker for region '{region}'")
    if end_idx is None:
        raise SystemExit(f"{path}: missing END marker for region '{region}'")
    if end_idx <= begin_idx:
        raise SystemExit(f"{path}: unpaired markers for region '{region}'")

    body = render_table(region)
    # Preserve the original newline style of the first line inside the region.
    newline = "\n" if "\n" in lines[begin_idx + 1] else ""
    new_body = body.replace("\n", newline)
    new_lines = (
        lines[: begin_idx + 1]
        + [new_body + newline if new_body else ""]
        + lines[end_idx:]
    )
    new_text = "".join(new_lines)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def stale_scan() -> list[tuple[str, str]]:
    """Search for stale scheme-count strings; return (path, line) hits."""
    n = len(SCHEME_NAMES)  # 15 named schemes (0..14); 255 is raw grayscale.
    # Stale count patterns: the current count is ``n`` named schemes (IDs
    # 0..n-1) plus raw grayscale 255. Anything spelling the previous count
    # (``n-1`` named schemes, IDs 0..n-2) or older is stale.
    patterns = [
        f"{n - 1} color scheme",
        f"`0`-`{n - 2}`",
        f"`0` to `{n - 2}`",
        f"0 to {n - 2}",
        f"{n - 1} + raw",
        f"{n - 1} named",
        f"{n - 2} color scheme",
    ]
    lower_patterns = [p.lower() for p in patterns]

    # Stale-count scan also covers raw grayscale (255) mentions of the old total.
    lower_patterns.append(f"{n - 1} color schemes".lower())

    files: list[Path] = []
    files.append(REPO_ROOT / "README.md")
    files.extend(sorted((REPO_ROOT / "docs").glob("*.md")))
    if (REPO_ROOT / "examples").exists():
        files.extend(
            p for p in (REPO_ROOT / "examples").rglob("*") if p.is_file()
        )

    hits: list[tuple[str, str]] = []
    for path in files:
        if _skip(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            for pat in lower_patterns:
                if pat in low:
                    hits.append((f"{path}:{lineno}", line))
                    break
    return hits


def _skip(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    for part in path.parts:
        if part in (".git", ".venv", "cache", "__pycache__"):
            return True
    if rel.startswith((".git/", ".venv/", "cache/", "__pycache__/")):
        return True
    # Skip binary files.
    try:
        with open(path, "rb") as fh:
            head = fh.read(8192)
    except OSError:
        return True
    return b"\x00" in head


def check_mode() -> int:
    problems = []
    for region, path in REGION_FILES.items():
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        begin_marker = _begin(region)
        end_marker = _end(region)
        begin_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if _strip(line) == begin_marker:
                begin_idx = i
            if _strip(line) == end_marker:
                end_idx = i
        if begin_idx is None or end_idx is None or end_idx <= begin_idx:
            problems.append((str(path), f"missing/unpaired markers for '{region}'"))
            continue
        current = "".join(lines[begin_idx + 1 : end_idx]).rstrip("\n")
        expected = render_table(region)
        if current != expected:
            problems.append(
                (str(path), f"region '{region}' is out of date")
            )

    for location, line in stale_scan():
        problems.append((location, f"stale: {line.strip()}"))

    # Verify the preview-PNG fingerprint stamp, so ``--check`` also catches
    # previews generated before the latest scheme / color-table / script
    # change.
    if not STAMP_PATH.exists():
        problems.append(
            (
                str(STAMP_PATH),
                "missing stamp - run scripts/generate_color_scheme_previews.py to (re)generate the preview PNGs",
            )
        )
    else:
        stamp = STAMP_PATH.read_text(encoding="utf-8").strip()
        if stamp != compute_preview_fingerprint(PREVIEW_SCRIPT):
            problems.append(
                (
                    str(STAMP_PATH),
                    "preview PNGs are stale - run scripts/generate_color_scheme_previews.py",
                )
            )

    if problems:
        for location, msg in problems:
            print(f"{location}: {msg}")
        return 1
    print("OK")
    return 0


def main() -> None:
    check = "--check" in sys.argv[1:]
    if check:
        raise SystemExit(check_mode())

    for region, path in REGION_FILES.items():
        changed = update_region(path, region)
        print(f"{path.relative_to(REPO_ROOT)}: {'updated' if changed else 'unchanged'}")


if __name__ == "__main__":
    main()
