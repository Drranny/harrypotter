"""
Run text-only retrieval experiments for Harry Potter corpus.

Blocks:
- E1: chunking strategy comparison (fixed/token/structure_text)
- E2: chunk size sweep (64/128/256/512, fixed vs structure_text)

Example:
    python3 scripts/run_text_experiments.py --run e1
    python3 scripts/run_text_experiments.py --run e2
"""

import argparse
import os
import subprocess
import sys
from typing import List


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK_SCRIPT = os.path.join(BASE_DIR, "scripts", "chunk_dataset.py")
INDEX_SCRIPT = os.path.join(BASE_DIR, "scripts", "build_index.py")
EVAL_SCRIPT = os.path.join(BASE_DIR, "scripts", "eval_retrieval.py")

TEXT_RAW_DIR = "data/text/raw"
TEXT_PROCESSED_DIR = "data/text/processed"
TEXT_EVAL_QUERIES = "data/text/eval/queries_text_main.jsonl"


def _run(cmd: List[str]) -> None:
    print("[RUN]", " ".join(cmd))
    subprocess.check_call(cmd, cwd=BASE_DIR)


def _ensure_dirs() -> None:
    os.makedirs(os.path.join(BASE_DIR, TEXT_PROCESSED_DIR), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "vector_db"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "results"), exist_ok=True)


def run_e1(results_dir: str, queries_path: str) -> None:
    _ensure_dirs()
    os.makedirs(os.path.join(BASE_DIR, results_dir), exist_ok=True)
    modes = ["fixed", "token", "structure_text"]
    chunk_size = 256
    overlap = 50

    for mode in modes:
        chunks_path = f"{TEXT_PROCESSED_DIR}/chunks_{mode}_{chunk_size}.json"
        metadata_path = f"{TEXT_PROCESSED_DIR}/chunks_{mode}_{chunk_size}_metadata.json"
        index_path = f"vector_db/faiss_text_{mode}_{chunk_size}.index"
        out_path = os.path.join(results_dir, f"text_e1_{mode}_{chunk_size}.json")

        _run(
            [
                sys.executable,
                CHUNK_SCRIPT,
                "--mode",
                mode,
                "--text-input-dir",
                TEXT_RAW_DIR,
                "--chunk-size",
                str(chunk_size),
                "--overlap",
                str(overlap),
                "--output",
                chunks_path,
            ]
        )
        _run(
            [
                sys.executable,
                INDEX_SCRIPT,
                "--chunks-path",
                chunks_path,
                "--index-path",
                index_path,
                "--metadata-path",
                metadata_path,
            ]
        )
        _run(
            [
                sys.executable,
                EVAL_SCRIPT,
                "--queries",
                queries_path,
                "--chunks",
                metadata_path,
                "--index",
                index_path,
                "--k",
                "5",
                "--out",
                out_path,
            ]
        )


def run_e2(results_dir: str, queries_path: str) -> None:
    _ensure_dirs()
    os.makedirs(os.path.join(BASE_DIR, results_dir), exist_ok=True)
    modes = ["fixed", "structure_text"]
    chunk_sizes = [64, 128, 256, 512]
    overlap = 50

    for mode in modes:
        for chunk_size in chunk_sizes:
            chunks_path = f"{TEXT_PROCESSED_DIR}/chunks_{mode}_{chunk_size}.json"
            metadata_path = f"{TEXT_PROCESSED_DIR}/chunks_{mode}_{chunk_size}_metadata.json"
            index_path = f"vector_db/faiss_text_{mode}_{chunk_size}.index"
            out_path = os.path.join(results_dir, f"text_e2_{mode}_{chunk_size}.json")

            _run(
                [
                    sys.executable,
                    CHUNK_SCRIPT,
                    "--mode",
                    mode,
                    "--text-input-dir",
                    TEXT_RAW_DIR,
                    "--chunk-size",
                    str(chunk_size),
                    "--overlap",
                    str(overlap),
                    "--output",
                    chunks_path,
                ]
            )
            _run(
                [
                    sys.executable,
                    INDEX_SCRIPT,
                    "--chunks-path",
                    chunks_path,
                    "--index-path",
                    index_path,
                    "--metadata-path",
                    metadata_path,
                ]
            )
            _run(
                [
                    sys.executable,
                    EVAL_SCRIPT,
                    "--queries",
                queries_path,
                    "--chunks",
                    metadata_path,
                    "--index",
                    index_path,
                    "--k",
                    "5",
                    "--out",
                    out_path,
                ]
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run text-only HP experiments")
    parser.add_argument("--run", choices=["e1", "e2", "all"], default="all")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--queries", default=TEXT_EVAL_QUERIES)
    args = parser.parse_args()

    if args.run in {"e1", "all"}:
        run_e1(args.results_dir, args.queries)
    if args.run in {"e2", "all"}:
        run_e2(args.results_dir, args.queries)

    print("[DONE] text experiments complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
