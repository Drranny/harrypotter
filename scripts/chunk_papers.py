"""
Backward-compatible entrypoint for text chunking.

This script preserves the original workflow documented in README/RAG_PIPELINE:
    python scripts/chunk_papers.py

Internally it delegates to scripts/chunk_dataset.py with mode=fixed.
"""

import os
import subprocess
import sys

from config import LEGACY_PROCESSED_DIR, LEGACY_RAW_DIR, TEXT_PROCESSED_DIR, TEXT_RAW_DIR


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(BASE_DIR, "scripts", "chunk_dataset.py")


def _first_existing_path(*candidates: str) -> str:
    for path in candidates:
        if os.path.exists(os.path.join(BASE_DIR, path)):
            return path
    return candidates[0]


def main() -> int:
    text_input_dir = _first_existing_path(TEXT_RAW_DIR, LEGACY_RAW_DIR)
    processed_dir = _first_existing_path(TEXT_PROCESSED_DIR, LEGACY_PROCESSED_DIR)

    cmd = [
        sys.executable,
        SCRIPT_PATH,
        "--mode",
        "fixed",
        "--text-input-dir",
        text_input_dir,
        "--output",
        os.path.join(processed_dir, "chunks.json"),
    ]

    print("[INFO] Running unified chunker in fixed mode for backward compatibility")
    return subprocess.call(cmd, cwd=BASE_DIR)


if __name__ == "__main__":
    raise SystemExit(main())
