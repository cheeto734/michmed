#!/usr/bin/env python3
"""Simple DB management script for dose-tracker.

Usage:
  python db_manager.py start   # create DB if missing
  python db_manager.py reset   # delete and recreate DB
"""

import argparse
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "dose_tracker.db"
SCHEMA_FILE = ROOT / "sql" / "schema.sql"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def create_schema(conn: sqlite3.Connection) -> None:
    with SCHEMA_FILE.open("r", encoding="utf-8") as f:
        conn.executescript(f.read())


def seed_default_user(conn: sqlite3.Connection) -> None:
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count > 0:
        return

    cursor = conn.execute("INSERT INTO users (username) VALUES (?)", (DEFAULT_USERNAME,))
    user_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO passwords (user_id, password) VALUES (?, ?)",
        (user_id, DEFAULT_PASSWORD),
    )


def start_db() -> None:
    if DB_FILE.exists():
        print(f"Database already exists: {DB_FILE}")
        return

    with sqlite3.connect(DB_FILE) as conn:
        create_schema(conn)
        seed_default_user(conn)
        conn.commit()

    print(f"Database created: {DB_FILE}")
    print(f"Default user: {DEFAULT_USERNAME} / {DEFAULT_PASSWORD}")


def reset_db() -> None:
    if DB_FILE.exists():
        DB_FILE.unlink()

    with sqlite3.connect(DB_FILE) as conn:
        create_schema(conn)
        seed_default_user(conn)
        conn.commit()

    print(f"Database reset: {DB_FILE}")
    print(f"Default user: {DEFAULT_USERNAME} / {DEFAULT_PASSWORD}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset or initialize the SQLite database.")
    parser.add_argument("action", choices=["start", "reset"], help="DB action to run")
    args = parser.parse_args()

    if args.action == "start":
        start_db()
    else:
        reset_db()


if __name__ == "__main__":
    main()
