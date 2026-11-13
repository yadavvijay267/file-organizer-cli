# File Organizer CLI

A command-line tool that sorts a messy folder into subfolders by file type,
date, or size — and can **undo** the last run, so it never destroys data.

![Status](https://img.shields.io/badge/status-working-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)

## Features

- **Sort by extension** (default), **modification date** (`YYYY-MM`
  folders), or **size** (Small / Medium / Large).
- **Dry-run mode** (`--dry-run`) — preview every move before anything
  changes.
- **Custom rules** — a YAML config maps your own folder names to file
  extensions (see `assets/rules-example.yaml`).
- **Undo log** — every real run writes `.organizer-undo.json` in the
  target folder; `--undo` moves everything back and removes empty folders.
- **Name collisions** are handled safely (`notes.txt` → `notes (1).txt`)
  instead of overwriting.
- **Demo mode** (`--demo`) — builds a sample messy folder and organises
  it so you can see the tool work in seconds.

## Tech Stack

- Python 3.9+ (standard library only: `argparse`, `pathlib`, `shutil`, `json`)
- `pytest` for tests (dev only)
- Optional: `PyYAML` for config files — without it, a built-in parser
  handles the simple `Category: [.ext, ...]` shape.

## How to Run

```bash
# See all options
python3 src/file_organizer.py --help

# Preview what would happen (nothing moves)
python3 src/file_organizer.py ~/Downloads --dry-run

# Actually organise a folder by file type
python3 src/file_organizer.py ~/Downloads

# Organise by date or size instead
python3 src/file_organizer.py ~/Downloads --by date
python3 src/file_organizer.py ~/Downloads --by size

# Use your own rules
python3 src/file_organizer.py ~/Downloads --config assets/rules-example.yaml

# Undo the last run
python3 src/file_organizer.py ~/Downloads --undo

# Try it without touching your files
python3 src/file_organizer.py --demo
```

See [docs/USAGE.md](docs/USAGE.md) for the full usage guide and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how it works inside.

## Sample Input

`assets/sample-messy/` contains a small messy folder you can copy and
organise yourself:

```bash
cp -r assets/sample-messy /tmp/messy
python3 src/file_organizer.py /tmp/messy --dry-run
python3 src/file_organizer.py /tmp/messy
```

## Screenshots

`screenshots/demo-output.txt` shows a real `--demo` run, and
[screenshots/SCREENSHOTS.md](screenshots/SCREENSHOTS.md) explains where
to put terminal screenshots.

## Tests

```bash
python3 -m pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Clamor.
