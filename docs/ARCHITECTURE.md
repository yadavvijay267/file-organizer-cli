# Architecture — File Organizer CLI

Single-file tool: `src/file_organizer.py` (standard library only).

## Flow

```
CLI args (argparse)
  └─ --demo → run_demo()            builds a temp messy folder, organises it
  └─ --undo → undo_last_run()       reverses .organizer-undo.json
  └─ else   → organize()
               ├─ plan_moves()      list (source, destination) pairs
               │    └─ folder_for() picks the destination folder
               │         ├─ extension → category_for() (config mapping)
               │         ├─ date      → YYYY-MM from mtime
               │         └─ size      → Small / Medium / Large
               ├─ --dry-run → print the plan, stop
               └─ real run  → shutil.move each file
                              └─ write_undo_log() → .organizer-undo.json
```

## Key decisions

- **Top level only, no recursion.** Organising recursively would move
  files out of folders the user arranged on purpose.
- **Undo log lives inside the target folder** (hidden file), so the log
  travels with the folder it describes and needs no global state.
- **Collision-safe destinations** via `unique_destination()` — a move
  never overwrites an existing file.
- **Config loading is dependency-optional.** PyYAML is preferred, but a
  15-line fallback parser covers the documented YAML shape, so the tool
  runs on a bare Python install.
- **Deterministic ordering.** `plan_moves()` sorts entries, so dry-run
  output is stable and diffable between runs.

## Tests

`tests/test_organizer.py` exercises the real functions against
`tmp_path` folders: extension/date/size grouping, dry-run, undo, the
undo-log contents, name collisions, custom config, and error paths.
Run with `python3 -m pytest tests/ -v`.
