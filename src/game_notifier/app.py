from __future__ import annotations

import atexit
from dataclasses import dataclass
import os
import threading
import time
import webbrowser

import requests
from .config import AppConfig, load_config
from .logging_setup import setup_logging
from .notifier import Notifier
from .paths import Paths, get_paths
from .tray import TrayController
from . import storage
from . import ui


@dataclass
class NotificationState:
    missed_games: int = 0


def calculate_backoff(retries: int, max_backoff: int) -> int:
    if retries == 1:
        return 2
    if retries == 2:
        return 5
    if retries == 3:
        return 10
    return min(max_backoff, 30 * (2 ** (retries - 4)))


class App:
    def __init__(self, paths: Paths | None = None, config: AppConfig | None = None) -> None:
        self._paths = paths or get_paths()
        self._config = config or load_config(self._paths.config_file)
        self._logger = setup_logging(
            self._paths.error_log,
            self._config.log_max_bytes,
            self._config.log_backup_count,
        )

        storage.ensure_dirs(
            self._paths.log_dir,
            self._paths.backup_dir,
        )

        # Ensure the SQLite DB and required tables/indexes exist on first run.
        try:
            storage._ensure_db(self._paths.db_file)
            storage._ensure_uploads_table(self._paths.db_file)
            storage._ensure_threads_table(self._paths.db_file)
            # Run a quick health check and attempt auto-restore if configured.
            healthy = storage.check_db_health(
                self._paths.db_file, self._paths.backup_dir, auto_restore=self._config.db_auto_restore
            )
            if not healthy and self._config.db_restore_prompt:
                # Alert user via logger and offer interactive restore dialog if possible.
                self._logger.warning("Database health check failed at startup; offering restore prompt.")
                try:
                    backups = storage.list_db_backups(self._paths.backup_dir)
                    if backups:
                        # show prompt (may raise TclError in headless envs)
                        sel = None
                        try:
                            sel = ui.prompt_db_restore(self._paths, backups)
                        except Exception:
                            sel = None

                        if sel is not None:
                            success = storage.restore_from_file(sel, self._paths.db_file)
                            try:
                                ui.show_restore_result(success, sel)
                            except Exception:
                                pass
                            if success:
                                self._logger.info(f"Restored DB from backup {sel}")
                            else:
                                self._logger.error("Failed to restore DB from selected backup")
                    else:
                        self._logger.warning("No DB backups available to restore from.")
                except Exception:
                    self._logger.exception("Error while attempting interactive DB restore")
        except Exception:
            # Non-fatal: proceed even if DB cannot be created here.
            self._logger.warning("Failed to ensure database/tables at startup", exc_info=True)

        self._state = NotificationState()
        self._stop_event = threading.Event()
        self._notifier = Notifier()
        self._tray = TrayController(
            default_icon=self._paths.icon_default,
            alert_icon=self._paths.icon_alert,
            get_missed=self._get_missed,
            on_read_logs=self._read_logs,
            on_clear=self._clear_notifications,
            on_analyze=self._show_analysis,
            on_quit=self._request_quit,
            on_restore_db=self._manual_restore_db,
            logger=self._logger,
            name=self._config.app_name.replace(" ", ""),
            title=self._config.app_name,
            count_label=self._config.tray_count_label,
        )

    def _get_missed(self) -> int:
        try:
            return storage.get_unread_count(self._paths.db_file)
        except Exception:
            return self._state.missed_games

    def _request_quit(self) -> None:
        self._stop_event.set()

    def _manual_restore_db(self) -> None:
        try:
            backups = storage.list_db_backups(self._paths.backup_dir)
            if not backups:
                self._logger.info("No DB backups available to restore from.")
                return
            try:
                sel = ui.prompt_db_restore(self._paths, backups)
            except Exception:
                sel = None
            if sel is None:
                return
            success = storage.restore_from_file(sel, self._paths.db_file)
            try:
                ui.show_restore_result(success, sel)
            except Exception:
                pass
            if success:
                self._logger.info(f"Restored DB from backup {sel}")
            else:
                self._logger.error("Failed to restore DB from selected backup")
        except Exception:
            self._logger.exception("Manual DB restore failed")
    

    def _notify(self, title: str, message: str, on_click=None) -> None:
        self._state.missed_games += 1
        self._notifier.show(title, message, on_click=on_click)
        self._tray.update()

    def _open_thread(self, item_id: str) -> None:
        template = self._config.item_url_template
        if not template:
            return
        webbrowser.open(template.format(id=item_id))

    def _normalize_item(self, raw: dict) -> dict:
        c = self._config
        creator_val = raw.get(c.field_creator) if c.field_creator else None
        return {
            "id": str(raw[c.field_id]),
            "ts": raw[c.field_timestamp],
            "title": raw.get(c.field_title, ""),
            "creator": creator_val,
        }

    def _build_request_url(self, base: str) -> str:
        unit = self._config.cache_buster_unit
        if unit == "ms":
            return f"{base}{int(time.time() * 1000)}"
        if unit == "s":
            return f"{base}{int(time.time())}"
        return base

    def _clear_notifications(self) -> None:
        # Mark all notifications as read (don't delete historical logs)
        try:
            storage.mark_all_seen(self._paths.db_file)
        except Exception:
            self._logger.error("Failed to mark notifications as seen", exc_info=True)
        self._state.missed_games = 0
        self._tray.update()

    def _read_logs(self) -> None:
        try:
            storage.mark_all_seen(self._paths.db_file)
        except Exception:
            pass
        self._tray.update()
        ui.open_logs(self._paths, self._config)

    def _show_analysis(self) -> None:
        ui.open_pattern(self._paths, self._config)

    def _fetch_games(self, url: str) -> list[dict] | None:
        response = requests.get(url, timeout=self._config.request_timeout)

        if response.status_code == 429:
            retry_after = int(
                response.headers.get("Retry-After", self._config.retry_after_default)
            )
            print(f"[RateLimit] Waiting {retry_after}s")
            time.sleep(retry_after)
            return None

        response.raise_for_status()
        result = response.json()
        for key in self._config.response_path:
            result = result[key]
        return result

    def _process_games(self, game_list: list[dict], known_data: dict[str, int]) -> None:
        new_games: list[dict] = []
        updated_games: list[dict] = []

        for raw in game_list:
            item = self._normalize_item(raw)
            tid = item["id"]
            ts = item["ts"]

            if tid not in known_data:
                new_games.append(item)
            elif ts > known_data[tid]:
                updated_games.append(item)

        if not new_games and not updated_games:
            return

        messages: list[str] = []
        try:
            if msg_new := storage.log_games(
                new_games, self._config.item_label_new, db_file=self._paths.db_file
            ):
                messages.append(msg_new)
        except Exception:
            self._logger.error("Failed to log new games to DB", exc_info=True)
            self._notify("Database Error", "Failed to persist notifications to DB.")


        try:
            if msg_updated := storage.log_games(
                updated_games, self._config.item_label_updated, db_file=self._paths.db_file
            ):
                messages.append(msg_updated)
        except Exception:
            self._logger.error("Failed to log updated games to DB", exc_info=True)
            self._notify("Database Error", "Failed to persist notifications to DB.")

        if messages:
            total_items = len(new_games) + len(updated_games)
            on_click = None
            if total_items == 1:
                only_item = (new_games + updated_games)[0]
                on_click = lambda item_id=only_item["id"]: self._open_thread(item_id)
            elif total_items > 1:
                on_click = lambda: ui.open_logs(self._paths, self._config)

            self._notify(f"{self._config.app_name} Alert", " and ".join(messages) + "!", on_click=on_click)

        for item in (new_games + updated_games):
            known_data[item["id"]] = item["ts"]
        storage.save_current_data(known_data, db_file=self._paths.db_file)

    def _check_games_loop(self) -> None:
        known_data = storage.load_previous_data(self._paths.db_file)
        first_run = True
        retries = 0

        while not self._stop_event.is_set():
            try:
                base_url = (
                    self._config.api_url_initial
                    if first_run
                    else self._config.api_url_poll
                )

                game_list = self._fetch_games(self._build_request_url(base_url))
                if game_list:
                    self._process_games(game_list, known_data)
                    retries = 0
                    first_run = False
                    delay = self._config.base_delay
                else:
                    delay = self._config.base_delay

            except requests.exceptions.Timeout:
                print("[Timeout] Quick retry")
                retries += 1
                delay = calculate_backoff(retries, self._config.max_backoff)

            except requests.exceptions.RequestException as e:
                print(f"[Network/HTTP Error] {e}")
                retries += 1
                delay = calculate_backoff(retries, self._config.max_backoff)

            except Exception:
                self._logger.error("Unexpected error", exc_info=True)
                retries += 1
                delay = calculate_backoff(retries, self._config.max_backoff)

                if retries >= 6:
                    self._notify(f"{self._config.app_name} Error", "Too many failed attempts.")
                    storage.compress_old_logs(
                        self._paths.error_log, self._config.log_backup_count
                    )
                    retries = 0
                    delay = self._config.max_backoff

            time.sleep(delay)

    def run(self) -> None:
        self._tray.start()  # blocks until tray setup completes (or times out)

        pid_file = self._paths.pid_file
        pid_file.write_text(str(os.getpid()))
        atexit.register(lambda: pid_file.unlink(missing_ok=True))

        checker_thread = threading.Thread(
            target=self._check_games_loop, daemon=True
        )
        checker_thread.start()

        while not self._stop_event.is_set():
            time.sleep(1)


def run() -> None:
    App().run()


if __name__ == "__main__":
    run()
