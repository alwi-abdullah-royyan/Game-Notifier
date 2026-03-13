from __future__ import annotations

from datetime import datetime
from pathlib import Path
import gzip
import shutil
import sqlite3
from typing import Iterable
from shutil import copyfile


def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def compress_old_logs(error_log: Path, backup_count: int) -> None:
    for i in range(1, backup_count + 1):
        file_name = Path(f"{error_log}.{i}")
        compressed_file = Path(str(file_name) + ".gz")

        if file_name.exists() and not compressed_file.exists():
            try:
                with file_name.open("rb") as f_in:
                    with gzip.open(compressed_file, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                file_name.unlink()
                print(f"Compressed {file_name.name} -> {compressed_file.name}")
            except Exception as e:
                print(f"Failed to compress {file_name.name}: {e}")


def _ensure_db(db_file: Path) -> None:
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                ts INTEGER,
                title TEXT,
                creator TEXT,
                label TEXT,
                seen INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Index for faster queries by timestamp and seen state
        cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_ts ON notifications(ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_seen ON notifications(seen)")
        conn.commit()
    finally:
        conn.close()


def _upsert_notifications(db_file: Path, games: Iterable[dict], label: str) -> None:
    if not games:
        return
    _ensure_db(db_file)
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        for g in games:
            gid = str(g["id"]) if g.get("id") is not None else None
            ts = int(g.get("ts") or 0)
            title = g.get("title") or ""
            creator = g.get("creator") or ""

            # If doesn't exist -> insert unseen; if exists and newer ts -> update ts/title/creator and mark unseen
            cur.execute("SELECT ts FROM notifications WHERE id = ?", (gid,))
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    "INSERT OR REPLACE INTO notifications (id, ts, title, creator, label, seen) VALUES (?, ?, ?, ?, ?, 0)",
                    (gid, ts, title, creator, label),
                )
            else:
                existing_ts = int(row[0] or 0)
                # If the incoming timestamp is newer or equal, treat it as a notification
                # event and mark as unseen so the UI/tray will surface it.
                if ts >= existing_ts:
                    cur.execute(
                        "UPDATE notifications SET ts = ?, title = ?, creator = ?, label = ?, seen = 0 WHERE id = ?",
                        (ts, title, creator, label, gid),
                    )
        conn.commit()
    finally:
        conn.close()


def get_unread_count(db_file: Path) -> int:
    if not db_file.exists():
        return 0
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM notifications WHERE seen = 0")
        row = cur.fetchone()
        return int(row[0] or 0)
    finally:
        conn.close()


def mark_all_seen(db_file: Path) -> None:
    if not db_file.exists():
        return
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute("UPDATE notifications SET seen = 1 WHERE seen = 0")
        conn.commit()
    finally:
        conn.close()


def get_recent_notifications(db_file: Path, limit: int = 100) -> list[dict]:
    if not db_file.exists():
        return []
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, ts, title, creator, label, seen, created_at FROM notifications ORDER BY ts DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "ts": r[1],
                "title": r[2],
                "creator": r[3],
                "label": r[4],
                "seen": bool(r[5]),
                "created_at": r[6],
            }
            for r in rows
        ]
    finally:
        conn.close()


def clear_notifications_db(db_file: Path) -> None:
    if not db_file.exists():
        return
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM notifications")
        conn.commit()
    finally:
        conn.close()


def delete_notification(db_file: Path, id: str) -> None:
    if not db_file.exists():
        return
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM notifications WHERE id = ?", (id,))
        conn.commit()
    finally:
        conn.close()


def mark_notification_seen(db_file: Path, id: str) -> None:
    if not db_file.exists():
        return
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute("UPDATE notifications SET seen = 1 WHERE id = ?", (id,))
        conn.commit()
    finally:
        conn.close()


def _ensure_uploads_table(db_file: Path) -> None:
    """Ensure the uploads table exists for imported upload timestamps."""
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                ts INTEGER PRIMARY KEY,
                ts_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Index on timestamps for range queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_uploads_ts ON uploads(ts)")
        conn.commit()
    finally:
        conn.close()


def get_uploads_count(db_file: Path) -> int:
    if not db_file.exists():
        return 0
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM uploads")
        row = cur.fetchone()
        return int(row[0] or 0)
    finally:
        conn.close()


def delete_old_uploads(db_file: Path, cutoff_ts: int) -> int:
    """Delete uploads with ts < cutoff_ts. Returns number of rows deleted."""
    if not db_file.exists():
        return 0
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM uploads WHERE ts < ?", (int(cutoff_ts),))
        deleted = cur.rowcount
        conn.commit()
        return deleted
    finally:
        conn.close()


def _ensure_threads_table(db_file: Path) -> None:
    """Ensure the threads table exists for known thread state."""
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                last_ts INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_threads_last_ts ON threads(last_ts)")
        conn.commit()
    finally:
        conn.close()


def check_db_health(db_file: Path, backup_dir: Path | None = None, auto_restore: bool = False) -> bool:
    """Perform a lightweight DB health check (PRAGMA integrity_check).

    If the check fails and auto_restore is True, attempt a restore from backups
    located under `backup_dir`. Returns True if DB is healthy or restored.
    """
    if not db_file.exists():
        return True  # fresh install — no DB yet is not a corruption
    try:
        conn = sqlite3.connect(db_file)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            rows = cur.fetchall()
            if rows and rows[0][0] == "ok":
                return True
            ok = False
        finally:
            conn.close()
    except Exception:
        ok = False

    if not ok and auto_restore and backup_dir is not None:
        try:
            return try_restore_from_backup(db_file, backup_dir)
        except Exception:
            return False

    return False


def try_restore_from_backup(db_file: Path, backup_dir: Path) -> bool:
    """Attempt to restore the DB from the latest backup file in backup_dir.

    On success returns True. On failure, leaves original DB moved to a .corrupt timestamped file.
    """
    if not backup_dir or not backup_dir.exists():
        return False

    backups = sorted(
        [p for p in backup_dir.iterdir() if p.name.startswith("notifications_db_backup_")],
        reverse=True,
    )
    if not backups:
        return False

    latest = backups[0]
    # Move current DB aside
    try:
        if db_file.exists():
            corrupt_name = db_file.with_suffix(f".corrupt.{int(datetime.now().timestamp())}")
            copyfile(db_file, corrupt_name)
            try:
                db_file.unlink()
            except Exception:
                pass

        copyfile(latest, db_file)

        # Quick integrity check
        conn = sqlite3.connect(db_file)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            rows = cur.fetchall()
            return bool(rows and rows[0][0] == "ok")
        finally:
            conn.close()
    except Exception:
        return False


def list_db_backups(backup_dir: Path) -> list[Path]:
    """Return sorted list of DB backup files (newest first)."""
    if not backup_dir.exists():
        return []
    backups = sorted(
        [p for p in backup_dir.iterdir() if p.name.startswith("notifications_db_backup_")],
        reverse=True,
    )
    return backups


def restore_from_file(backup_file: Path, db_file: Path) -> bool:
    """Restore the given backup file into `db_file`. Returns True on success."""
    if not backup_file.exists():
        return False
    try:
        # snapshot existing DB
        if db_file.exists():
            corrupt_name = db_file.with_suffix(f".corrupt.{int(datetime.now().timestamp())}")
            copyfile(db_file, corrupt_name)
            try:
                db_file.unlink()
            except Exception:
                pass

        copyfile(backup_file, db_file)

        conn = sqlite3.connect(db_file)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            rows = cur.fetchall()
            return bool(rows and rows[0][0] == "ok")
        finally:
            conn.close()
    except Exception:
        return False


def load_previous_data(db_file: Path) -> dict[str, int]:
    """Load previous known threads from DB only."""
    if not db_file.exists():
        return {}
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, last_ts FROM threads")
        rows = cur.fetchall()
        return {str(r[0]): int(r[1] or 0) for r in rows}
    finally:
        conn.close()


def save_current_data(data_dict: dict[str, int], db_file: Path) -> None:
    """Save known thread data to DB only."""
    _ensure_threads_table(db_file)
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        for tid, ts in data_dict.items():
            cur.execute(
                "INSERT OR REPLACE INTO threads (id, last_ts) VALUES (?, ?)",
                (str(tid), int(ts or 0)),
            )
        conn.commit()
    finally:
        conn.close()


def log_games(games: list[dict], label: str, db_file: Path) -> str | None:
    if not games:
        return None

    _ensure_db(db_file)
    _upsert_notifications(db_file, games, label)
    _ensure_uploads_table(db_file)
    conn = sqlite3.connect(db_file)
    try:
        cur = conn.cursor()
        for g in games:
            ts = int(g.get("ts") or 0)
            ts_text = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts > 0 else None
            cur.execute("INSERT OR IGNORE INTO uploads (ts, ts_text) VALUES (?, ?)", (ts, ts_text))
        conn.commit()
    finally:
        conn.close()

    return f"{len(games)} {label}"


def backup_database(db_file: Path, backup_dir: Path, max_backups: int = 5) -> None:
    """Create timestamped backups of the SQLite DB and rotate old backups."""
    if not db_file.exists():
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    # Only create backup if DB changed since latest backup to avoid frequent duplicates.
    backups = sorted(
        [p for p in backup_dir.iterdir() if p.name.startswith("notifications_db_backup_")],
        reverse=True,
    )

    try:
        db_mtime = db_file.stat().st_mtime
    except Exception:
        db_mtime = None

    if backups and db_mtime is not None:
        try:
            latest = backups[0]
            latest_mtime = latest.stat().st_mtime
            # If DB hasn't been modified since the latest backup, skip creating a new one.
            if db_mtime <= latest_mtime:
                return
        except Exception:
            # If any issue reading backup metadata, fall through and attempt backup.
            pass

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"notifications_db_backup_{timestamp}.sqlite"
    try:
        shutil.copy(db_file, backup_file)
    except Exception:
        return

    # Rotate
    # Rotate backups to keep only the newest `max_backups` files
    backups = sorted(
        [p for p in backup_dir.iterdir() if p.name.startswith("notifications_db_backup_")],
        reverse=True,
    )
    for i, b_path in enumerate(backups):
        if i >= max_backups:
            try:
                b_path.unlink()
            except Exception:
                pass


# log-file clearing removed in DB-only mode
