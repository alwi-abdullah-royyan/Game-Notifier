from pathlib import Path
import sys
import argparse

root = Path(__file__).resolve().parents[1]
src_dir = root / "src"
sys.path.insert(0, str(src_dir))

from game_notifier.paths import get_paths
from game_notifier import storage


def main():
    parser = argparse.ArgumentParser(description="Restore DB from backups")
    parser.add_argument("--latest", action="store_true", help="Restore from latest backup without prompting")
    parser.add_argument("--list", action="store_true", help="List available backups")
    args = parser.parse_args()

    paths = get_paths()
    backups = storage.list_db_backups(paths.backup_dir)
    if not backups:
        print("No backups found.")
        return

    if args.list:
        for i, b in enumerate(backups):
            print(f"[{i}] {b.name} ({b.stat().st_size} bytes)")
        return

    if args.latest:
        sel = backups[0]
    else:
        for i, b in enumerate(backups):
            print(f"[{i}] {b.name} ({b.stat().st_size} bytes)")
        try:
            idx = int(input("Select backup index to restore (or blank to cancel): ").strip() or -1)
        except Exception:
            print("Cancelled")
            return
        if idx < 0 or idx >= len(backups):
            print("Cancelled")
            return
        sel = backups[idx]

    print(f"Restoring from {sel}...")
    ok = storage.restore_from_file(sel, paths.db_file)
    if ok:
        print("Restore succeeded.")
    else:
        print("Restore failed.")


if __name__ == '__main__':
    main()
