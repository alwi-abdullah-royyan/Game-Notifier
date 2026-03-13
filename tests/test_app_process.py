from pathlib import Path
from types import SimpleNamespace

from src.game_notifier.app import App
from src.game_notifier import storage


def test_process_games_calls_log_games_once_per_bucket(tmp_path: Path, monkeypatch):
    app = App.__new__(App)

    app._paths = SimpleNamespace(
        log_dir=tmp_path / "logs",
        db_file=tmp_path / "notifications.db",
    )
    app._config = SimpleNamespace(
        field_id="thread_id",
        field_timestamp="ts",
        field_title="title",
        field_creator="creator",
        item_url_template="https://example/{id}",
        item_label_new="new game(s)",
        item_label_updated="updated game(s)",
        app_name="Test Notifier",
    )
    app._logger = SimpleNamespace(error=lambda *args, **kwargs: None)
    app._notify = lambda *args, **kwargs: None

    calls: list[str] = []

    def fake_log_games(games, label, db_file):
        calls.append(label)
        if games:
            return f"{len(games)} {label}"
        return None

    monkeypatch.setattr(storage, "log_games", fake_log_games)
    monkeypatch.setattr(storage, "save_current_data", lambda *args, **kwargs: None)

    game_list = [
        {"thread_id": "1", "ts": 100, "title": "A", "creator": "X"},
        {"thread_id": "2", "ts": 200, "title": "B", "creator": "Y"},
    ]

    app._process_games(game_list, known_data={})

    # exactly one call for new bucket and one for updated bucket
    assert calls.count("new game(s)") == 1
    assert calls.count("updated game(s)") == 1
