"""SQLite foundation integration tests."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from limen.persistence import SCHEMA_VERSION, Database


def test_database_initializes_wal_and_schema(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        assert database.connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert database.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert database.connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        tables = {
            row[0]
            for row in database.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"providers", "events", "schema_meta"}.issubset(tables)
    finally:
        database.close()

    second_database = Database(tmp_path / "state.db")
    second_database.open()
    second_database.close()


def test_unversioned_existing_schema_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "state.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE legacy (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()

    database = Database(database_path)
    with pytest.raises(sqlite3.DatabaseError, match="Unversioned"):
        database.open()


def test_incomplete_versioned_schema_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "state.db"
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA user_version = 1")
    connection.commit()
    connection.close()

    database = Database(database_path)
    with pytest.raises(sqlite3.DatabaseError, match="incomplete"):
        database.open()


def test_transaction_rolls_back_on_constraint_failure(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            with database.transaction() as connection:
                connection.execute(
                    "INSERT INTO providers(key_id, provider, deployment, api_key_fingerprint, "
                    "limit_scope, status, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("key-1", "test", "model", "fingerprint", "invalid", "active", 1),
                )
        assert database.connection.execute("SELECT COUNT(*) FROM providers").fetchone()[0] == 0

        with pytest.raises(ValueError, match="application failure"):
            with database.transaction():
                raise ValueError("application failure")
        assert database.connection.in_transaction is False
    finally:
        database.close()
