#!/usr/bin/env python3
"""file-organizer-cli — sort a messy folder into subfolders.

Sorts the files in a directory by extension, by modification date, or by
size. Every real run writes an undo log (``.organizer-undo.json`` inside the
target folder) so the last run can be reversed with ``--undo``.

Usage:
    python3 src/file_organizer.py ~/Downloads --dry-run
    python3 src/file_organizer.py ~/Downloads --by date
    python3 src/file_organizer.py ~/Downloads --config rules.yaml
    python3 src/file_organizer.py ~/Downloads --undo
    python3 src/file_organizer.py --demo

Only the Python standard library is used. A YAML config file is supported
when PyYAML is installed; otherwise a small built-in parser handles the
simple ``Category: [.ext, ...]`` shape used by the example config.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

UNDO_FILENAME = ".organizer-undo.json"
VERSION = "1.0.0"

# Default extension -> folder mapping (used when no --config is given).
DEFAULT_CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".odt", ".rtf"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Presentations": {".ppt", ".pptx", ".odp", ".key"},
    "Audio": {".mp3", ".wav", ".flac", ".ogg", ".m4a"},
    "Video": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "Archives": {".zip", ".tar", ".gz", ".rar", ".7z"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".java", ".c", ".cpp"},
}

DEMO_FILES = {
    "holiday-photo.jpg": "fake image bytes (demo)\n",
    "notes.txt": "demo notes\n",
    "budget-2026.xlsx": "fake spreadsheet (demo)\n",
    "song.mp3": "fake audio (demo)\n",
    "report.pdf": "fake pdf (demo)\n",
    "archive.zip": "fake archive (demo)\n",
    "script.py": "# demo script\n",
    "presentation.pptx": "fake slides (demo)\n",
}


def load_config(path: Path) -> dict[str, set[str]]:
    """Load a ``Category: [.ext, ...]`` mapping from a YAML file.

    Prefers PyYAML when available; falls back to a minimal parser that
    understands exactly this shape, so the tool still works without it.
    """
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {
            str(category): {e.lower() if e.startswith(".") else "." + e.lower()
                            for e in exts}
            for category, exts in data.items()
        }
    except ImportError:
        pass
    categories: dict[str, set[str]] = {}
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")) and line.rstrip().endswith(":"):
            current = line.rstrip(":").strip()
            categories[current] = set()
        elif current and line.strip().startswith("-"):
            ext = line.strip().lstrip("-").strip().strip("'\"").lower()
            if ext:
                categories[current].add(ext if ext.startswith(".") else "." + ext)
    return categories


def category_for(path: Path, categories: dict[str, set[str]]) -> str:
    ext = path.suffix.lower()
    for name, exts in categories.items():
        if ext in exts:
            return name
    return "Other" if ext else "No extension"


def folder_for(path: Path, mode: str, categories: dict[str, set[str]]) -> str:
    if mode == "date":
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m")
    if mode == "size":
        size = path.stat().st_size
        if size < 1_000_000:
            return "Small (under 1 MB)"
        if size < 10_000_000:
            return "Medium (1-10 MB)"
        return "Large (over 10 MB)"
    return category_for(path, categories)


def unique_destination(folder: Path, name: str) -> Path:
    """Return a non-colliding destination inside *folder* for *name*."""
    dest = folder / name
    if not dest.exists():
        return dest
    stem, suffix = Path(name).stem, Path(name).suffix
    i = 1
    while True:
        candidate = folder / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def plan_moves(target: Path, mode: str, categories: dict[str, set[str]]):
    """Return the list of (source, destination) moves for *target*."""
    moves = []
    for entry in sorted(target.iterdir()):
        if not entry.is_file():
            continue
        if entry.name == UNDO_FILENAME:
            continue
        dest_folder = target / folder_for(entry, mode, categories)
        moves.append((entry, unique_destination(dest_folder, entry.name)))
    return moves


def write_undo_log(target: Path, moves) -> None:
    log = {
        "moves": [
            {"from": str(src), "to": str(dst)} for src, dst in moves
        ]
    }
    (target / UNDO_FILENAME).write_text(json.dumps(log, indent=2), encoding="utf-8")


def load_undo_log(target: Path):
    log_path = target / UNDO_FILENAME
    if not log_path.exists():
        return None
    return json.loads(log_path.read_text(encoding="utf-8"))


def undo_last_run(target: Path) -> int:
    log = load_undo_log(target)
    if not log or not log.get("moves"):
        print(f"No undo log found in {target} — nothing to undo.")
        return 1
    undone = 0
    for move in reversed(log["moves"]):
        src, dst = Path(move["to"]), Path(move["from"])
        if not src.exists():
            print(f"  skipped (already gone): {src.name}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(unique_destination(dst.parent, dst.name)))
        undone += 1
        print(f"  restored: {src.name} -> {dst.parent.name}/")
    (target / UNDO_FILENAME).unlink(missing_ok=True)
    # Remove folders left empty by the undo.
    for child in target.iterdir():
        if child.is_dir() and not any(child.iterdir()):
            child.rmdir()
    print(f"Undid {undone} move(s).")
    return 0


def show_tree(root: Path, prefix: str = "") -> None:
    entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    for i, entry in enumerate(entries):
        last = i == len(entries) - 1
        print(f"{prefix}{'└── ' if last else '├── '}{entry.name}")
        if entry.is_dir():
            show_tree(entry, prefix + ("    " if last else "│   "))


def organize(target: Path, mode: str, categories, dry_run: bool) -> int:
    if not target.is_dir():
        print(f"Error: {target} is not a directory.", file=sys.stderr)
        return 2
    moves = plan_moves(target, mode, categories)
    if not moves:
        print(f"Nothing to organise in {target} — no files found.")
        return 0
    print(f"{'Would move' if dry_run else 'Moving'} {len(moves)} file(s) in {target} (by {mode}):")
    for src, dst in moves:
        print(f"  {src.name}  ->  {dst.parent.name}/{dst.name}")
    if dry_run:
        print("Dry run — nothing was moved. Run without --dry-run to apply.")
        return 0
    for src, dst in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    write_undo_log(target, moves)
    print(f"Done. {len(moves)} file(s) organised. Undo with: --undo")
    return 0


def run_demo() -> int:
    """Build a messy temp folder, organise it, and show before/after."""
    demo_dir = Path(tempfile.mkdtemp(prefix="organizer-demo-"))
    for name, content in DEMO_FILES.items():
        (demo_dir / name).write_text(content, encoding="utf-8")
    print(f"Demo folder: {demo_dir}\nBefore:")
    show_tree(demo_dir)
    print("\nOrganising by extension…")
    code = organize(demo_dir, "extension", DEFAULT_CATEGORIES, dry_run=False)
    print("\nAfter:")
    show_tree(demo_dir)
    print(f"\nDemo complete. The organised folder is left at: {demo_dir}")
    print("Run with --undo on that folder to see the undo log in action.")
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file_organizer.py",
        description="Sort a messy folder into subfolders by extension, date, or size.",
        epilog="Every real run writes .organizer-undo.json in the target folder; "
               "--undo reverses the last run.",
    )
    parser.add_argument("directory", nargs="?", type=Path,
                        help="folder to organise (omit with --demo or --undo needs one)")
    parser.add_argument("--by", choices=["extension", "date", "size"],
                        default="extension",
                        help="how to group files (default: extension)")
    parser.add_argument("--dry-run", action="store_true",
                        help="preview the moves without moving anything")
    parser.add_argument("--config", type=Path,
                        help="YAML file mapping folder names to file extensions")
    parser.add_argument("--undo", action="store_true",
                        help="reverse the last organise run in the folder")
    parser.add_argument("--demo", action="store_true",
                        help="build a sample messy folder and organise it")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.demo:
        return run_demo()
    if args.directory is None:
        print("Error: a directory is required (or use --demo).", file=sys.stderr)
        return 2
    if args.undo:
        return undo_last_run(args.directory)
    categories = DEFAULT_CATEGORIES
    if args.config:
        if not args.config.is_file():
            print(f"Error: config file not found: {args.config}", file=sys.stderr)
            return 2
        categories = load_config(args.config)
        print(f"Loaded {len(categories)} custom categories from {args.config}")
    return organize(args.directory, args.by, categories, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
