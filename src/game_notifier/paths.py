from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Paths:
    root: Path
    config_file: Path
    log_dir: Path
    error_log: Path
    backup_dir: Path
    icon_default: Path
    icon_alert: Path
    db_file: Path
    pid_file: Path


def get_paths(root: Optional[Path] = None) -> Paths:
    if root is None:
        root = Path(__file__).resolve().parents[2]

    config_dir = root / "config"
    data_dir = root / "data"
    log_dir = root / "logs"
    assets_dir = root / "assets"
    backup_dir = data_dir / "backups"

    return Paths(
        root=root,
        config_file=config_dir / "config.json",
        log_dir=log_dir,
        error_log=log_dir / "error.log",
        backup_dir=backup_dir,
        icon_default=assets_dir / "1.ico",
        icon_alert=assets_dir / "1_alert.ico",
        db_file=data_dir / "notifications.db",
        pid_file=data_dir / "game-notifier.pid",
    )
