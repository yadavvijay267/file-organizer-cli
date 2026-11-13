"""Tests for file_organizer.py — run with:  python3 -m pytest tests/ -v

The tests build real messy folders inside pytest's tmp_path, organise them,
and assert on the real filesystem. No network, no fixtures on disk.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import file_organizer as fo


def make_messy(tmp_path, files=("photo.jpg", "notes.txt", "song.mp3", "data.csv")):
    for name in files:
        (tmp_path / name).write_text("demo content", encoding="utf-8")
    return tmp_path


def test_organize_by_extension_moves_files(tmp_path):
    make_messy(tmp_path)
    code = fo.organize(tmp_path, "extension", fo.DEFAULT_CATEGORIES, dry_run=False)
    assert code == 0
    assert (tmp_path / "Images" / "photo.jpg").exists()
    assert (tmp_path / "Documents" / "notes.txt").exists()
    assert (tmp_path / "Audio" / "song.mp3").exists()
    assert (tmp_path / "Spreadsheets" / "data.csv").exists()
    assert not (tmp_path / "photo.jpg").exists()


def test_dry_run_moves_nothing(tmp_path):
    make_messy(tmp_path)
    code = fo.organize(tmp_path, "extension", fo.DEFAULT_CATEGORIES, dry_run=True)
    assert code == 0
    assert (tmp_path / "photo.jpg").exists()
    assert not (tmp_path / "Images").exists()
    assert not (tmp_path / fo.UNDO_FILENAME).exists()


def test_undo_restores_files(tmp_path):
    make_messy(tmp_path)
    fo.organize(tmp_path, "extension", fo.DEFAULT_CATEGORIES, dry_run=False)
    assert (tmp_path / "Images" / "photo.jpg").exists()
    code = fo.undo_last_run(tmp_path)
    assert code == 0
    assert (tmp_path / "photo.jpg").exists()
    assert not (tmp_path / "Images").exists()
    assert not (tmp_path / fo.UNDO_FILENAME).exists()


def test_undo_log_records_every_move(tmp_path):
    make_messy(tmp_path, files=("a.txt", "b.txt"))
    fo.organize(tmp_path, "extension", fo.DEFAULT_CATEGORIES, dry_run=False)
    log = json.loads((tmp_path / fo.UNDO_FILENAME).read_text(encoding="utf-8"))
    assert len(log["moves"]) == 2
    assert all("from" in m and "to" in m for m in log["moves"])


def test_organize_by_date_groups_by_year_month(tmp_path):
    import os
    from datetime import datetime

    target = make_messy(tmp_path, files=("old.txt",))
    stamp = datetime(2024, 3, 15, 12, 0).timestamp()
    os.utime(target / "old.txt", (stamp, stamp))
    code = fo.organize(target, "date", fo.DEFAULT_CATEGORIES, dry_run=False)
    assert code == 0
    assert (target / "2024-03" / "old.txt").exists()


def test_organize_by_size_groups_by_size(tmp_path):
    target = make_messy(tmp_path, files=("tiny.txt",))
    (target / "big.bin").write_bytes(b"x" * 2_000_000)
    code = fo.organize(target, "size", fo.DEFAULT_CATEGORIES, dry_run=False)
    assert code == 0
    assert (target / "Small (under 1 MB)" / "tiny.txt").exists()
    assert (target / "Medium (1-10 MB)" / "big.bin").exists()


def test_unknown_extension_goes_to_other(tmp_path):
    make_messy(tmp_path, files=("weird.xyz",))
    fo.organize(tmp_path, "extension", fo.DEFAULT_CATEGORIES, dry_run=False)
    assert (tmp_path / "Other" / "weird.xyz").exists()


def test_name_collision_gets_numbered(tmp_path):
    make_messy(tmp_path, files=("notes.txt",))
    (tmp_path / "Documents").mkdir()
    (tmp_path / "Documents" / "notes.txt").write_text("existing", encoding="utf-8")
    fo.organize(tmp_path, "extension", fo.DEFAULT_CATEGORIES, dry_run=False)
    assert (tmp_path / "Documents" / "notes (1).txt").exists()


def test_custom_config_categories(tmp_path):
    config = tmp_path / "rules.yaml"
    config.write_text("Photos:\n  - .jpg\n", encoding="utf-8")
    categories = fo.load_config(config)
    assert categories == {"Photos": {".jpg"}}
    make_messy(tmp_path, files=("pic.jpg", "doc.txt"))
    fo.organize(tmp_path, "extension", categories, dry_run=False)
    assert (tmp_path / "Photos" / "pic.jpg").exists()
    assert (tmp_path / "Other" / "doc.txt").exists()


def test_empty_folder_is_a_noop(tmp_path):
    assert fo.organize(tmp_path, "extension", fo.DEFAULT_CATEGORIES, dry_run=False) == 0


def test_missing_directory_returns_error(tmp_path):
    assert fo.organize(tmp_path / "nope", "extension", fo.DEFAULT_CATEGORIES, dry_run=False) == 2
