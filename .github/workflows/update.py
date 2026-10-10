"""Compatibility entry point for offline source-link generation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from combine.sources import main

if __name__ == '__main__':
    raise SystemExit(main())
