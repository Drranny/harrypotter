#!/usr/bin/env python3
"""
Evaluate text structure metrics from chunk metadata.

Current metrics:
- Boundary Truncation Ratio
- Context Augmentation Ratio (small-chunk context policy usage)
"""

import argparse
import glob
import json
import os
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate structure metrics for text chunks")
    parser.add_argument(
        "--chunks-glob",
        default="data/text/processed/chunks_*_metadata.json",
        help="Glob pattern for chunk metadata JSON files",
    )
    parser.add_argument(
        "--only-modes",
        default="fixed,structure_text,token",
        help="Comma-separated chunk modes to include",
    )
    parser.add_argument(
        "--out",
        default="results/text_structure_metrics.json",
        help="Output JSON path",
    )
    return parser.parse_args()


def _looks_truncated(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    if stripped.endswith((".", "?", "!", '"', "'", "”", "’", ")", "]", "}")):
        return False
    if stripped.endswith((":", ";", ",")):
        return True
    return True


def _infer_setting_from_path(path: str) -> str:
    name = os.path.basename(path)
    prefix = "chunks_"
    suffix = "_metadata.json"
    if name.startswith(prefix) and name.endswith(suffix):
        return name[len(prefix) : -len(suffix)]
    return name


def _is_allowed_mode(setting: str, allowed_modes: List[str]) -> bool:
    return any(setting.startswith(mode + "_") for mode in allowed_modes)


def evaluate_file(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    total = len(chunks)
    if total == 0:
        return {
            "setting": _infer_setting_from_path(path),
            "path": path,
            "chunk_count": 0,
            "boundary_truncation_ratio": 0.0,
            "context_augmentation_ratio": 0.0,
            "explicit_boundary_flags": 0,
        }

    boundary_truncated = 0
    context_augmented = 0
    explicit_boundary_flags = 0

    for chunk in chunks:
        text = chunk.get("text", "")
        metadata = chunk.get("metadata", {}) or {}

        if metadata.get("context_augmented"):
            context_augmented += 1

        if "boundary_truncated" in metadata:
            explicit_boundary_flags += 1
            if bool(metadata.get("boundary_truncated")):
                boundary_truncated += 1
        else:
            if _looks_truncated(text):
                boundary_truncated += 1

    return {
        "setting": _infer_setting_from_path(path),
        "path": path,
        "chunk_count": total,
        "boundary_truncation_ratio": boundary_truncated / total,
        "context_augmentation_ratio": context_augmented / total,
        "explicit_boundary_flags": explicit_boundary_flags,
    }


def main() -> int:
    args = parse_args()
    allowed_modes = [m.strip() for m in args.only_modes.split(",") if m.strip()]
    paths = sorted(glob.glob(args.chunks_glob))

    rows: List[Dict] = []
    for path in paths:
        setting = _infer_setting_from_path(path)
        if allowed_modes and not _is_allowed_mode(setting, allowed_modes):
            continue
        rows.append(evaluate_file(path))

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    rows = sorted(rows, key=lambda r: r["setting"])
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"results": rows}, f, ensure_ascii=False, indent=2)

    print(f"[DONE] files={len(rows)} output={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
