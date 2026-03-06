"""Управление подключением к базе данных SQLite."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from .schema import SCHEMA_SQL


class Database:
    """Предоставляет подключение SQLite и инициализацию схемы."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._logger = logging.getLogger(self.__class__.__name__)

    def initialize(self) -> None:
        """Инициализировать SQLite и создать схему при необходимости."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(SCHEMA_SQL)
            self._apply_migrations(connection)
            connection.commit()
        self._logger.info("SQLite initialized at %s", self._db_path)

    def connect(self) -> sqlite3.Connection:
        """Создать новое подключение SQLite с включенным row_factory."""
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _apply_migrations(self, connection: sqlite3.Connection) -> None:
        """Применить миграции для уже существующих таблиц."""
        columns = connection.execute("PRAGMA table_info(alerts)").fetchall()
        existing_columns = {str(row["name"]) for row in columns}

        if "acknowledged" not in existing_columns:
            connection.execute(
                "ALTER TABLE alerts ADD COLUMN acknowledged INTEGER NOT NULL DEFAULT 0"
            )
            self._logger.info("Migration applied: alerts.acknowledged added")

        if "acknowledged_at" not in existing_columns:
            connection.execute("ALTER TABLE alerts ADD COLUMN acknowledged_at TEXT")
            self._logger.info("Migration applied: alerts.acknowledged_at added")
