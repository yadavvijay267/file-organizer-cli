# Usage — File Organizer CLI

## Basic usage

```
python3 src/file_organizer.py <directory> [options]
```

| Flag | What it does |
|---|---|
| `--by extension` | Group by file type — `Images/`, `Documents/`, `Audio/`, … (default) |
| `--by date` | Group by modification month — `2026-11/`, `2026-10/`, … |
| `--by size` | Group by size — `Small (under 1 MB)`, `Medium (1-10 MB)`, `Large (over 10 MB)` |
| `--dry-run` | Print the planned moves, move nothing |
| `--config FILE` | YAML file mapping folder names to extensions |
| `--undo` | Reverse the last organise run in the folder |
| `--demo` | Build a sample messy folder and organise it |
| `--help` | Show all options (exits 0) |
| `--version` | Show the version |

## Default categories

Images, Documents, Spreadsheets, Presentations, Audio, Video, Archives,
Code. Files matching no category go to `Other/`; files with no extension
go to `No extension/`. The full mapping is in `DEFAULT_CATEGORIES` at the
top of `src/file_organizer.py`.

## Custom rules (YAML)

```yaml
Photos:
  - .jpg
  - .png
Invoices:
  - .pdf
```

```bash
python3 src/file_organizer.py ~/Downloads --config my-rules.yaml
```

If PyYAML is installed it is used; otherwise a small built-in parser
handles this exact shape, so the tool works with zero dependencies.

## Undo — how it works

After a real (non-dry-run) organise, the folder contains a hidden file,
`.organizer-undo.json`, listing every move (`from` → `to`). `--undo`
reads that file, moves each file back in reverse order, deletes the log,
and removes any folders left empty. Dry runs never write a log.

**Limits:** the undo log only covers the *last* run — organising the same
folder twice overwrites it. Files you delete or move by hand after a run
are skipped (not an error) during undo.

## Safety notes

- Only files in the **top level** of the folder are moved; subfolders are
  left alone, and the tool never recurses.
- A file is never overwritten: if `Documents/notes.txt` already exists,
  the moved file becomes `Documents/notes (1).txt`.
- Always run `--dry-run` first on a folder you care about.
