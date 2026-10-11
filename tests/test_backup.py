import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import backup as backup_module


class FakeSettings:
    def __init__(self, database_url):
        self.database_url = database_url


def test_backup_and_restore_roundtrip(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("create table leads (id integer primary key, name text)")
    conn.execute("insert into leads (name) values ('table for 4')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(backup_module, "get_settings", lambda: FakeSettings(f"sqlite:///{db_path.as_posix()}"))

    backup_path = backup_module.backup(dest_dir=tmp_path / "backups")
    assert backup_path.exists()

    # simulate data loss
    conn = sqlite3.connect(str(db_path))
    conn.execute("delete from leads")
    conn.commit()
    conn.close()

    backup_module.restore(backup_path)

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("select name from leads").fetchall()
    conn.close()
    assert rows == [("table for 4",)]


def test_restore_saves_a_safety_copy_of_the_live_db_first(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("create table leads (id integer primary key, name text)")
    conn.execute("insert into leads (name) values ('original')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(backup_module, "get_settings", lambda: FakeSettings(f"sqlite:///{db_path.as_posix()}"))
    backup_path = backup_module.backup(dest_dir=tmp_path / "backups")

    conn = sqlite3.connect(str(db_path))
    conn.execute("update leads set name = 'changed after backup'")
    conn.commit()
    conn.close()

    backup_module.restore(backup_path)

    safety_copy = db_path.with_name("app.before_restore.db")
    assert safety_copy.exists()
    conn = sqlite3.connect(str(safety_copy))
    rows = conn.execute("select name from leads").fetchall()
    conn.close()
    assert rows == [("changed after backup",)]


def test_backup_raises_for_non_sqlite_url(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_module, "get_settings", lambda: FakeSettings("postgresql://user:pass@localhost/db"))
    with pytest.raises(SystemExit):
        backup_module.backup(dest_dir=tmp_path / "backups")


def test_backup_raises_when_no_database_exists(tmp_path, monkeypatch):
    missing_db = tmp_path / "does_not_exist.db"
    monkeypatch.setattr(backup_module, "get_settings", lambda: FakeSettings(f"sqlite:///{missing_db.as_posix()}"))
    with pytest.raises(SystemExit):
        backup_module.backup(dest_dir=tmp_path / "backups")


def test_restore_raises_for_missing_backup_file(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setattr(backup_module, "get_settings", lambda: FakeSettings(f"sqlite:///{db_path.as_posix()}"))
    with pytest.raises(SystemExit):
        backup_module.restore(tmp_path / "nonexistent_backup.db")
