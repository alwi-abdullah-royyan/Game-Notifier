# Game Notifier

A generic Windows/Linux/macOS system-tray notifier for game or content update feeds.
Polls a JSON API and fires desktop notifications when new or updated items appear.

---

## Requirements

- Python 3.10+
- A JSON API endpoint that returns a list of items (field names are configurable)

---

## Setup

```sh
# 1. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 2. Install the package and its dependencies
pip install -e .

# 3. Copy the example config and fill in your API URLs
copy config\config_example.json config\config.json   # Windows
cp config/config_example.json config/config.json      # Linux / macOS
```

---

## Configuration

All settings live in `config/config.json` (never committed — see `.gitignore`).
Copy `config/config_example.json` as a starting point.

| Key                 | Required | Description                                                               |
| ------------------- | -------- | ------------------------------------------------------------------------- |
| `API_URL90`         | ✓        | URL for the initial fetch (e.g. last 90 rows)                             |
| `API_URL15`         | ✓        | URL for subsequent polls (e.g. last 15 rows)                              |
| `APP_NAME`          |          | Display name shown in tray and notifications (default: `Game Notifier`)   |
| `ITEM_URL_TEMPLATE` |          | URL opened on notification click — use `{id}` as placeholder              |
| `RESPONSE_PATH`     |          | JSON keys to traverse to reach the item list (default: `["msg", "data"]`) |
| `FIELD_ID`          |          | Item ID field name in the API response (default: `thread_id`)             |
| `FIELD_TIMESTAMP`   |          | Timestamp field name (default: `ts`)                                      |
| `FIELD_TITLE`       |          | Title field name (default: `title`)                                       |
| `FIELD_CREATOR`     |          | Creator/author field name, or `null` to omit (default: `creator`)         |
| `CACHE_BUSTER_UNIT` |          | Append timestamp to URL: `"ms"`, `"s"`, or `null` (default: `"ms"`)       |
| `BASE_DELAY`        |          | Seconds between polls (default: `120`)                                    |
| `MAX_BACKOFF`       |          | Max retry back-off in seconds (default: `300`)                            |
| `DB_AUTO_RESTORE`   |          | Auto-restore DB from backup on corruption (default: `false`)              |
| `DB_RESTORE_PROMPT` |          | Show restore dialog on startup if DB is unhealthy (default: `true`)       |
| `DB_BACKUP_MAX`     |          | Number of rolling DB backups to keep (default: `5`)                       |

---

## Running

### Windows

```bat
bin\start.bat    # launch tray app (no console window)
bin\stop.bat     # stop the running instance
bin\test.bat     # run tests
```

For auto-start on login, add a shortcut to `bin\start.bat` in your Windows Startup folder (`shell:startup`).

### Linux / macOS

```sh
chmod +x bin/*.sh
bin/start.sh     # launch tray app in background
bin/stop.sh      # stop via PID file
bin/test.sh      # run tests
```

---

## Project structure

```
bин/                      platform launchers (start / stop / test)
config/
  config_example.json   template — copy to config.json and edit
  config.json           your local config (gitignored)
scripts/                utility CLI tools
  analyze.py            open Upload Pattern analysis tab
  read_log.py           open Logs tab
  restore_db.py         list or restore DB backups from CLI
src/game_notifier/      core package
assets/                 tray icons
data/                   runtime DB and backups (gitignored)
logs/                   runtime logs (gitignored)
```

---

## CLI utilities

```sh
python scripts/restore_db.py --list     # list available backups
python scripts/restore_db.py --latest   # restore the most recent backup
python scripts/analyze.py               # open analysis window
python scripts/read_log.py              # open log viewer
```
