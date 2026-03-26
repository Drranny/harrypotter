#!/usr/bin/env python3
"""
Run LLM generation evaluation for all available code chunk settings.

Default settings discovered from:
- data/processed/code_*_metadata.json
- vector_db/faiss_code_*.index

Output files:
- results/code_generation_<setting>.json
"""

import argparse
import glob
import os
import subprocess
import sys
from typing import List


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_SCRIPT = os.path.join(BASE_DIR, "scripts", "eval_code_generation.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all code generation evals with LLM mode")
    parser.add_argument("--queries", default="data/eval/queries_code.jsonl")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--max-queries", type=int, default=0)
    parser.add_argument("--support-threshold", type=float, default=0.35)
    parser.add_argument("--answer-language", default="English")
    parser.add_argument("--out-dir", default="results")
    return parser.parse_args()


def discover_settings() -> List[str]:
    chunk_paths = glob.glob(os.path.join(BASE_DIR, "data/processed/code_*_metadata.json"))
    settings: List[str] = []
    for path in chunk_paths:
        setting = os.path.basename(path).replace("code_", "").replace("_metadata.json", "")
        index_path = os.path.join(BASE_DIR, f"vector_db/faiss_code_{setting}.index")
        if os.path.exists(index_path):
            settings.append(setting)
    return sorted(set(settings))


def run_cmd(cmd: List[str]) -> None:
    print("[RUN]", " ".join(cmd))
    subprocess.check_call(cmd, cwd=BASE_DIR)


def main() -> int:
    args = parse_args()
    settings = discover_settings()

    if not settings:
        print("[ERROR] No valid setting found. Need both code_*_metadata.json and matching faiss_code index.")
        return 1

    os.makedirs(os.path.join(BASE_DIR, args.out_dir), exist_ok=True)

    for setting in settings:
        chunks = f"data/processed/code_{setting}_metadata.json"
        index = f"vector_db/faiss_code_{setting}.index"
        out = os.path.join(args.out_dir, f"code_generation_{setting}.json")

        cmd = [
            sys.executable,
            EVAL_SCRIPT,
            "--queries",
            args.queries,
            "--chunks",
            chunks,
            "--index",
            index,
            "--k",
            str(args.k),
            "--answer-mode",
            "llm",
            "--answer-language",
            args.answer_language,
            "--support-threshold",
            str(args.support_threshold),
            "--save-full-transcript",
            "--out",
            out,
        ]
        if args.max_queries > 0:
            cmd.extend(["--max-queries", str(args.max_queries)])

        run_cmd(cmd)

    print("[DONE] all code generation settings completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())