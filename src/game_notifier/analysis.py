from collections import Counter
from datetime import datetime, timedelta, date
from pathlib import Path
import statistics

from . import storage
import sqlite3


def _normalize_epoch(ts: int) -> int | None:
    if ts <= 0:
        return None
    # Heuristic: milliseconds vs seconds
    if ts >= 1_000_000_000_000:
        return ts // 1000
    return ts


def _prev_data_stats(db_file: Path) -> dict:
    stats = {
        "total_games_logged": 0,
        "oldest_timestamp": None,
    }

    data = storage.load_previous_data(db_file)
    if not data:
        return stats

    normalized = [_normalize_epoch(ts) for ts in data.values()]
    normalized = [ts for ts in normalized if ts]
    if not normalized:
        return stats

    oldest_ts = min(normalized)
    oldest_dt = datetime.fromtimestamp(oldest_ts)
    stats["total_games_logged"] = len(data)
    stats["oldest_timestamp"] = oldest_dt.strftime("%Y-%m-%d %H:%M:%S")
    return stats


def analyze_upload_frequencies_data(
    backup_dir: Path,
    max_backups: int = 5,
    db_file: Path | None = None,
    prune_db: bool = True,
) -> tuple[list[dict], dict]:
    if db_file is None:
        raise ValueError("db_file is required in DB-only mode")

    try:
        storage.backup_database(db_file, backup_dir, max_backups=max_backups)
    except Exception:
        # non-fatal: if DB backup fails, continue without blocking analysis
        pass

    prev_stats = _prev_data_stats(db_file)

    if db_file.exists():
        # Prefer DB-backed uploads table
        conn = sqlite3.connect(db_file)
        try:
            cur = conn.cursor()
            cur.execute("SELECT ts, ts_text FROM uploads ORDER BY ts ASC")
            rows_iter = cur.fetchall()
        finally:
            conn.close()

        cutoff_time = datetime.now() - timedelta(days=30)
        hour_counter = Counter()
        daily_hour_counter: dict[date, set[int]] = {}
        daily_counter = Counter()
        uploads_today_per_hour = Counter()

        recent_ts_values: list[int] = []
        today_date = datetime.today().date()

        for r in rows_iter:
            ts = int(r[0] or 0)
            if ts <= 0:
                continue
            dt = datetime.fromtimestamp(ts)
            if dt >= cutoff_time:
                hour_counter[dt.hour] += 1
                recent_ts_values.append(ts)
                daily_counter[dt.date()] += 1

                if dt.date() not in daily_hour_counter:
                    daily_hour_counter[dt.date()] = set()
                daily_hour_counter[dt.date()].add(dt.hour)

                if dt.date() == today_date:
                    uploads_today_per_hour[dt.hour] += 1

        # Optionally prune old rows from DB
        if prune_db:
            cutoff_ts = int((cutoff_time).timestamp())
            try:
                deleted = storage.delete_old_uploads(db_file, cutoff_ts)
            except Exception:
                deleted = 0

        # compute stats from DB-derived counters
        active_days = list(daily_hour_counter.keys())
        total_days = len(active_days)
        prob_per_hour: dict[int, float] = {}
        avg_per_hour: dict[int, float] = {}

        for hour in range(24):
            days_with_hour = sum(
                1 for day_hours in daily_hour_counter.values() if hour in day_hours
            )
            prob_per_hour[hour] = (days_with_hour / total_days * 100) if total_days else 0

            total_hour = hour_counter.get(hour, 0)
            avg_per_hour[hour] = (total_hour / total_days) if total_days else 0

        daily_totals = list(daily_counter.values())
        median_daily = statistics.median(daily_totals) if daily_totals else 0
        total_uploads_today = sum(uploads_today_per_hour.values())
        remaining_estimate = max(median_daily - total_uploads_today, 0)
        total_upload_events = len(recent_ts_values)

        rows: list[dict] = []
        for hour in range(24):
            rows.append(
                {
                    "hour": f"{hour:02d}:00",
                    "total": hour_counter.get(hour, 0),
                    "today": uploads_today_per_hour.get(hour, 0),
                    "avg": round(avg_per_hour[hour], 2),
                    "prob": round(prob_per_hour[hour], 1),
                }
            )

        summary = {
            "median_daily": median_daily,
            "total_uploads_today": total_uploads_today,
            "remaining_estimate": remaining_estimate,
            "total_upload_events": total_upload_events,
            **prev_stats,
        }
        return rows, summary

    summary = {
        "median_daily": 0,
        "total_uploads_today": 0,
        "remaining_estimate": 0,
        "total_upload_events": 0,
        **prev_stats,
        "message": "No database found yet.",
    }
    return [], summary


def analyze_upload_frequencies(
    backup_dir: Path,
    max_backups: int = 5,
    db_file: Path | None = None,
) -> str:
    rows, summary = analyze_upload_frequencies_data(
        backup_dir, max_backups=max_backups, db_file=db_file
    )

    if "message" in summary:
        message = summary["message"]
    else:
        message = None

    result = ["Upload frequency (last 30 days):"]
    result.append("Hour | Total uploads | Today uploads | Avg per day | Probability (%)")
    result.append("-----|---------------|---------------|------------|----------------")
    for row in rows:
        result.append(
            f"{row['hour']} | {row['total']} | {row['today']} | {row['avg']:.2f} | {row['prob']:.1f}"
        )

    result.append(f"\nMedian total uploads per day: {summary['median_daily']}")
    result.append(f"Total uploads today so far: {summary['total_uploads_today']}")
    result.append(
        "Estimated remaining uploads today (median-based): "
        f"{summary['remaining_estimate']}"
    )
    result.append(f"Total upload events (last 30 days): {summary['total_upload_events']}")

    oldest = summary.get("oldest_timestamp")
    if summary.get("total_games_logged", 0) and oldest:
        result.append(
            f"Total games logged since {oldest}: {summary['total_games_logged']}"
        )
    else:
        result.append("Total games logged: 0")

    if message:
        result.append(f"\n{message}")

    return "\n".join(result)


if __name__ == "__main__":
    from game_notifier.paths import get_paths

    paths = get_paths()
    print(
        analyze_upload_frequencies(
            paths.backup_dir, db_file=paths.db_file
        )
    )
