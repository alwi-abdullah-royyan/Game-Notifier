from pathlib import Path
import time
import sqlite3

import pytest

from src.game_notifier import storage


def test_db_upsert_and_unread(tmp_path: Path):
    db = tmp_path / "notifications.db"
    # ensure db created and table exists
    storage._ensure_db(db)

    games = [
        {"id": "1", "ts": int(time.time()), "title": "Game A", "creator": "Alice"},
        {"id": "2", "ts": int(time.time()), "title": "Game B", "creator": "Bob"},
    ]

    storage._upsert_notifications(db, games, "new game(s)")
    assert storage.get_unread_count(db) == 2

    # mark one as seen
    storage.mark_notification_seen(db, "1")
    assert storage.get_unread_count(db) == 1

    # delete one
    storage.delete_notification(db, "2")
    assert storage.get_unread_count(db) == 0

    # clear all
    storage._upsert_notifications(db, games, "new game(s)")
    assert storage.get_unread_count(db) == 2
    storage.clear_notifications_db(db)
    assert storage.get_unread_count(db) == 0


def test_save_current_data_db_failure_does_not_fallback_to_json(tmp_path: Path, monkeypatch):
    db = tmp_path / "notifications.db"
    json_file = tmp_path / "prev_data.json"

    def _fail_connect(*args, **kwargs):
        raise sqlite3.OperationalError("db down")

    monkeypatch.setattr(storage.sqlite3, "connect", _fail_connect)

    with pytest.raises(sqlite3.OperationalError):
        storage.save_current_data({"1": 123}, db_file=db)

    assert not json_file.exists()
