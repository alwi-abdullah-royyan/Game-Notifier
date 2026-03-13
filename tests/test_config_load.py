import json
from pathlib import Path

from src.game_notifier.config import load_config, AppConfig


def test_load_legacy_and_new_configs(tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    # legacy
    legacy = {"API_URL": "https://legacy/api?_="}
    (cfg_dir / "legacy.json").write_text(json.dumps(legacy), encoding="utf-8")
    cfg = load_config(cfg_dir / "legacy.json")
    assert cfg.api_url_initial == "https://legacy/api?_="
    assert cfg.api_url_poll == "https://legacy/api?_="

    # new format
    new = {
        "API_URL90": "https://api/90?_=",
        "API_URL15": "https://api/15?_=",
        "RESPONSE_PATH": ["m", "d"],
        "FIELD_ID": "identifier",
        "FIELD_TIMESTAMP": "timestamp",
    }
    (cfg_dir / "new.json").write_text(json.dumps(new), encoding="utf-8")
    cfg2 = load_config(cfg_dir / "new.json")
    assert cfg2.api_url_initial == "https://api/90?_="
    assert cfg2.api_url_poll == "https://api/15?_="
    assert cfg2.response_path == ("m", "d")
    assert cfg2.field_id == "identifier"
    assert cfg2.field_timestamp == "timestamp"
