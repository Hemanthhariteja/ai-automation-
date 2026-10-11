"""DB backup/restore for the SQLite deployment path.

    python -m app.backup backup                 # writes a timestamped copy to backend/backups/
    python -m app.backup restore <path-to-file>  # overwrites the live DB with that backup

Uses SQLite's own backup API (sqlite3.Connection.backup) rather than a raw
file copy, so it's safe to run against a database the server is currently
using — SQLite handles the concurrent read consistently, a plain file copy
would not.

Postgres deployments (the schema is Postgres-portable — see
docs/ARCHITECTURE.md) should use `pg_dump`/`pg_restore` instead; this script
is SQLite-only, matching the ₹0-mandatory-cost default deployment path.
"""

import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BACKUP_DIR = BACKEND_DIR / "backups"


def _sqlite_path_from_url(database_url: str) -> Path:
    if not database_url.startswith("sqlite"):
        raise SystemExit(
            f"This script only backs up SQLite databases; DATABASE_URL is '{database_url}'. "
            "For Postgres, use pg_dump/pg_restore instead."
        )
    # sqlite:///./app.db -> ./app.db, resolved relative to backend/ (the
    # working directory every doc in this repo runs the server from).
    raw_path = database_url.split("///", 1)[1]
    return (BACKEND_DIR / raw_path).resolve()


def backup(dest_dir: Path = DEFAULT_BACKUP_DIR) -> Path:
    db_path = _sqlite_path_from_url(get_settings().database_url)
    if not db_path.exists():
        raise SystemExit(f"No database found at {db_path} — nothing to back up.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest_path = dest_dir / f"app_backup_{timestamp}.db"

    source_conn = sqlite3.connect(str(db_path))
    dest_conn = sqlite3.connect(str(dest_path))
    with dest_conn:
        source_conn.backup(dest_conn)
    source_conn.close()
    dest_conn.close()

    print(f"Backed up {db_path} -> {dest_path}")
    return dest_path


def restore(backup_path: Path) -> None:
    if not backup_path.exists():
        raise SystemExit(f"Backup file not found: {backup_path}")

    db_path = _sqlite_path_from_url(get_settings().database_url)
    print(f"This will OVERWRITE the current database at {db_path} with {backup_path}.")

    if db_path.exists():
        safety_copy = db_path.with_name(f"{db_path.stem}.before_restore.db")
        shutil.copy2(db_path, safety_copy)
        print(f"(Current database saved first, just in case: {safety_copy})")

    source_conn = sqlite3.connect(str(backup_path))
    dest_conn = sqlite3.connect(str(db_path))
    with dest_conn:
        source_conn.backup(dest_conn)
    source_conn.close()
    dest_conn.close()

    print(f"Restored {backup_path} -> {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("backup", help="Write a timestamped backup to backend/backups/")

    restore_parser = subparsers.add_parser("restore", help="Overwrite the live DB with a backup file")
    restore_parser.add_argument("backup_file", help="Path to a .db file previously written by 'backup'")

    args = parser.parse_args()

    if args.command == "backup":
        backup()
    elif args.command == "restore":
        restore(Path(args.backup_file))


if __name__ == "__main__":
    main()
