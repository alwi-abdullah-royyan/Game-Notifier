from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from game_notifier.paths import get_paths
from game_notifier.config import load_config
from game_notifier.ui import run_standalone


if __name__ == "__main__":
    paths = get_paths()
    config = load_config(paths.config_file)
    run_standalone("pattern", paths, config)
