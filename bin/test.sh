#!/usr/bin/env sh
# Run the test suite using the venv's Python.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
"$DIR/.venv/bin/python" -m pytest -q "$@"
