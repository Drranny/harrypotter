#!/usr/bin/env python3
"""
Run the full text-track experiment pipeline for the paper setup.

Stages:
1. Retrieval experiments
2. Structure metrics
3. LLM generation experiments
4. Answer correctness evaluation
5. Artifact aggregation
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from typing import List


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full text-track experiment pipeline")
    parser.add_argument("--retrieval-run", choices=["e1", "e2", "all"], default="all")
    parser.add_argument("--queries", default="data/text/eval/queries_text_benchmark30.jsonl")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--max-queries", type=int, default=0)
    parser.add_argument("--support-threshold", type=float, default=0.35)
    parser.add_argument("--run-tag", default="")
    return parser.parse_args()


def _run(cmd: List[str]) -> None:
    print("[RUN]", " ".join(cmd))
    subprocess.check_call(cmd, cwd=BASE_DIR)


def main() -> int:
    args = parse_args()
    run_tag = args.run_tag or datetime.now().strftime("text_run_%Y%m%d_%H%M%S")
    run_dir = os.path.join("results", "runs", run_tag)
    retrieval_dir = os.path.join(run_dir, "retrieval")
    generation_dir = os.path.join(run_dir, "generation")
    tables_dir = os.path.join(run_dir, "tables")
    figures_dir = os.path.join(run_dir, "figures")
    structure_metrics_path = os.path.join(run_dir, "text_structure_metrics.json")
    correctness_summary_path = os.path.join(run_dir, "text_answer_correctness_summary.csv")
    correctness_detailed_path = os.path.join(run_dir, "text_answer_correctness_detailed.csv")
    metrics_path = os.path.join(run_dir, "text_metrics.csv")
    failure_notes_path = os.path.join(run_dir, "text_failure_notes.md")
    markdown_summary_path = os.path.join(tables_dir, "text_metrics_summary.md")
    analysis_notes_path = os.path.join(run_dir, "analysis_notes.md")

    for path in [run_dir, retrieval_dir, generation_dir, tables_dir, figures_dir]:
        os.makedirs(os.path.join(BASE_DIR, path), exist_ok=True)

    _run(
        [
            sys.executable,
            "scripts/run_text_experiments.py",
            "--run",
            args.retrieval_run,
            "--queries",
            args.queries,
            "--results-dir",
            retrieval_dir,
        ]
    )

    _run(
        [
            sys.executable,
            "scripts/eval_text_structure_metrics.py",
            "--chunks-glob",
            "data/text/processed/chunks_*_metadata.json",
            "--only-modes",
            "fixed,structure_text,token",
            "--out",
            structure_metrics_path,
        ]
    )

    generation_cmd = [
        sys.executable,
        "scripts/run_text_generation_all.py",
        "--queries",
        args.queries,
        "--k",
        str(args.k),
        "--support-threshold",
        str(args.support_threshold),
        "--out-dir",
        generation_dir,
    ]
    if args.max_queries > 0:
        generation_cmd.extend(["--max-queries", str(args.max_queries)])
    _run(generation_cmd)

    _run(
        [
            sys.executable,
            "scripts/eval_answer_correctness.py",
            "--generation-glob",
            os.path.join(generation_dir, "text_generation_*.json"),
            "--out-summary",
            correctness_summary_path,
            "--out-detailed",
            correctness_detailed_path,
        ]
    )

    _run(
        [
            sys.executable,
            "scripts/build_text_analysis_artifacts.py",
            "--retrieval-summary",
            os.path.join(retrieval_dir, "text_experiment_summary_q30.csv"),
            "--retrieval-details-glob",
            os.path.join(retrieval_dir, "text_*.json"),
            "--structure-metrics",
            structure_metrics_path,
            "--generation-glob",
            os.path.join(generation_dir, "text_generation_*.json"),
            "--answer-correctness",
            correctness_summary_path,
            "--out-metrics",
            metrics_path,
            "--tables-dir",
            tables_dir,
            "--figures-dir",
            figures_dir,
            "--analysis-notes-out",
            analysis_notes_path,
            "--failure-notes-out",
            failure_notes_path,
            "--markdown-summary-out",
            markdown_summary_path,
        ]
    )

    print(f"[DONE] full text pipeline completed: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
