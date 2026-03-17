#!/usr/bin/env python3
"""
Build text-track analysis artifacts:
- results/text_metrics.csv
- results/text_failure_notes.md
- results/tables/text_*.csv
- results/figures/text_*.md
- docs/analysis_notes.md (text section)
"""

import argparse
import csv
import glob
import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build text analysis artifacts")
    parser.add_argument(
        "--retrieval-summary",
        default="results/text_experiment_summary_q30.csv",
        help="CSV with retrieval summary (optional)",
    )
    parser.add_argument(
        "--retrieval-details-glob",
        default="results/text_*_q30.json",
        help="Glob for per-setting retrieval detail JSON",
    )
    parser.add_argument(
        "--structure-metrics",
        default="results/text_structure_metrics.json",
        help="JSON path from eval_text_structure_metrics.py",
    )
    parser.add_argument(
        "--generation-glob",
        default="results/text_generation_*.json",
        help="Glob for generation metric JSON",
    )
    parser.add_argument(
        "--answer-correctness",
        default="results/text_answer_correctness_summary.csv",
        help="CSV path from eval_answer_correctness.py",
    )
    parser.add_argument("--out-metrics", default="results/text_metrics.csv")
    parser.add_argument("--tables-dir", default="results/tables")
    parser.add_argument("--figures-dir", default="results/figures")
    parser.add_argument("--analysis-notes-out", default="docs/analysis_notes.md")
    parser.add_argument("--failure-notes-out", default="results/text_failure_notes.md")
    parser.add_argument("--markdown-summary-out", default="results/tables/text_metrics_summary.md")
    return parser.parse_args()


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: str, rows: List[Dict], fieldnames: List[str]) -> None:
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _format_md_value(value: float, highlight: bool = False) -> str:
    formatted = f"{value:.2f}"
    return f"**{formatted}**" if highlight else formatted


def _normalize_setting(name: str) -> str:
    setting = name
    setting = re.sub(r"^text_e[12]_", "", setting)
    setting = re.sub(r"_q30$", "", setting)
    return setting


def _parse_chunk_size(setting: str) -> int:
    try:
        return int(setting.split("_")[-1])
    except ValueError:
        return -1


def main() -> int:
    args = parse_args()
    tables_dir = args.tables_dir
    figures_dir = args.figures_dir
    analysis_notes_out = args.analysis_notes_out
    failure_notes_out = args.failure_notes_out
    markdown_summary_out = args.markdown_summary_out

    retrieval_by_setting: Dict[str, Dict] = {}

    if os.path.exists(args.retrieval_summary):
        summary_rows = _read_csv(args.retrieval_summary)
        for row in summary_rows:
            setting = _normalize_setting(row["name"])
            retrieval_by_setting[setting] = {
                "hit_at_1": float(row["hit_at_1"]),
                "hit_at_5": float(row["hit_at_5"]),
                "mrr": float(row["mrr"]),
                "ndcg_at_10": float(row["ndcg_at_10"]),
            }

    # Override with latest per-setting JSON metrics when available.
    for path in sorted(glob.glob(args.retrieval_details_glob)):
        setting = _normalize_setting(os.path.basename(path).replace(".json", ""))
        metrics = _load_json(path).get("metrics", {})
        if not metrics:
            continue
        retrieval_by_setting[setting] = {
            "hit_at_1": float(metrics.get("hit_rate_at_1", 0.0)),
            "hit_at_5": float(metrics.get("hit_rate_at_k", 0.0)),
            "mrr": float(metrics.get("mrr", 0.0)),
            "ndcg_at_10": float(metrics.get("ndcg_at_k", 0.0)),
        }

    structure_map: Dict[str, Dict] = {}
    if os.path.exists(args.structure_metrics):
        structure_rows = _load_json(args.structure_metrics).get("results", [])
        for row in structure_rows:
            structure_map[row["setting"]] = row

    generation_map: Dict[str, Dict] = {}
    for path in sorted(glob.glob(args.generation_glob)):
        data = _load_json(path)
        metrics = data.get("metrics", {})
        setting = os.path.basename(path).replace("text_generation_", "").replace(".json", "")
        generation_map[setting] = metrics

    correctness_map: Dict[str, Dict] = {}
    if os.path.exists(args.answer_correctness):
        for row in _read_csv(args.answer_correctness):
            correctness_map[row["setting"]] = {
                "exact_match": float(row.get("exact_match", 0.0)),
                "fact_exact_match": float(row.get("fact_exact_match", 0.0)),
                "entity_recall": float(row.get("entity_recall", 0.0)),
                "fact_entity_recall": float(row.get("fact_entity_recall", 0.0)),
                "semantic_similarity": float(row.get("semantic_similarity", 0.0)),
            }

    merged_rows: List[Dict] = []
    for setting in sorted(retrieval_by_setting):
        retrieval = retrieval_by_setting[setting]
        structure = structure_map.get(setting, {})
        generation = generation_map.get(setting, {})
        correctness = correctness_map.get(setting, {})
        merged_rows.append(
            {
                "setting": setting,
                "hit_at_1": f"{retrieval['hit_at_1']:.6f}",
                "hit_at_5": f"{retrieval['hit_at_5']:.6f}",
                "mrr": f"{retrieval['mrr']:.6f}",
                "ndcg_at_10": f"{retrieval['ndcg_at_10']:.6f}",
                "boundary_truncation_ratio": f"{float(structure.get('boundary_truncation_ratio', 0.0)):.6f}",
                "context_augmentation_ratio": f"{float(structure.get('context_augmentation_ratio', 0.0)):.6f}",
                "answer_relevance": f"{float(generation.get('answer_relevance', 0.0)):.6f}",
                "faithfulness": f"{float(generation.get('faithfulness', 0.0)):.6f}",
                "exact_match": f"{float(correctness.get('exact_match', 0.0)):.6f}",
                "fact_exact_match": f"{float(correctness.get('fact_exact_match', 0.0)):.6f}",
                "entity_recall": f"{float(correctness.get('entity_recall', 0.0)):.6f}",
                "fact_entity_recall": f"{float(correctness.get('fact_entity_recall', 0.0)):.6f}",
                "semantic_similarity": f"{float(correctness.get('semantic_similarity', 0.0)):.6f}",
            }
        )

    _write_csv(
        args.out_metrics,
        merged_rows,
        [
            "setting",
            "hit_at_1",
            "hit_at_5",
            "mrr",
            "ndcg_at_10",
            "boundary_truncation_ratio",
            "context_augmentation_ratio",
            "answer_relevance",
            "faithfulness",
            "exact_match",
            "fact_exact_match",
            "entity_recall",
            "fact_entity_recall",
            "semantic_similarity",
        ],
    )

    markdown_rows: List[Dict] = []
    if merged_rows:
        metrics_for_max = [
            "hit_at_1",
            "hit_at_5",
            "mrr",
            "ndcg_at_10",
            "answer_relevance",
            "faithfulness",
        ]
        metrics_for_min = ["boundary_truncation_ratio"]
        max_values = {
            metric: max(float(row[metric]) for row in merged_rows) for metric in metrics_for_max
        }
        min_values = {
            metric: min(float(row[metric]) for row in merged_rows) for metric in metrics_for_min
        }

        for row in merged_rows:
            markdown_rows.append(
                {
                    "setting": row["setting"],
                    "hit_at_1": _format_md_value(
                        float(row["hit_at_1"]),
                        float(row["hit_at_1"]) == max_values["hit_at_1"],
                    ),
                    "hit_at_5": _format_md_value(
                        float(row["hit_at_5"]),
                        float(row["hit_at_5"]) == max_values["hit_at_5"],
                    ),
                    "mrr": _format_md_value(
                        float(row["mrr"]),
                        float(row["mrr"]) == max_values["mrr"],
                    ),
                    "ndcg_at_10": _format_md_value(
                        float(row["ndcg_at_10"]),
                        float(row["ndcg_at_10"]) == max_values["ndcg_at_10"],
                    ),
                    "boundary_truncation_ratio": _format_md_value(
                        float(row["boundary_truncation_ratio"]),
                        float(row["boundary_truncation_ratio"]) == min_values["boundary_truncation_ratio"],
                    ),
                    "answer_relevance": _format_md_value(
                        float(row["answer_relevance"]),
                        float(row["answer_relevance"]) == max_values["answer_relevance"],
                    ),
                    "faithfulness": _format_md_value(
                        float(row["faithfulness"]),
                        float(row["faithfulness"]) == max_values["faithfulness"],
                    ),
                }
            )

    os.makedirs(tables_dir, exist_ok=True)
    with open(markdown_summary_out, "w", encoding="utf-8") as f:
        f.write("| setting | hit@1 | hit@5 | mrr | ndcg@10 | boundary_trunc | answer_rel | faithful |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for row in markdown_rows:
            f.write(
                f"| {row['setting']} | {row['hit_at_1']} | {row['hit_at_5']} | {row['mrr']} | "
                f"{row['ndcg_at_10']} | {row['boundary_truncation_ratio']} | "
                f"{row['answer_relevance']} | {row['faithfulness']} |\n"
            )

    full_markdown_out = os.path.join(tables_dir, "text_metrics_full_summary.md")
    with open(full_markdown_out, "w", encoding="utf-8") as f:
        f.write(
            "| setting | hit@1 | hit@5 | mrr | ndcg@10 | boundary_trunc | answer_rel | "
            "faithful | exact_match | fact_exact_match | entity_recall | fact_entity_recall | semantic_similarity |\n"
        )
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for row in merged_rows:
            f.write(
                f"| {row['setting']} | "
                f"{float(row['hit_at_1']):.2f} | "
                f"{float(row['hit_at_5']):.2f} | "
                f"{float(row['mrr']):.2f} | "
                f"{float(row['ndcg_at_10']):.2f} | "
                f"{float(row['boundary_truncation_ratio']):.2f} | "
                f"{float(row['answer_relevance']):.2f} | "
                f"{float(row['faithfulness']):.2f} | "
                f"{float(row['exact_match']):.2f} | "
                f"{float(row['fact_exact_match']):.2f} | "
                f"{float(row['entity_recall']):.2f} | "
                f"{float(row['fact_entity_recall']):.2f} | "
                f"{float(row['semantic_similarity']):.2f} |\n"
            )

    os.makedirs(figures_dir, exist_ok=True)
    analysis_notes_dir = os.path.dirname(analysis_notes_out)
    if analysis_notes_dir:
        os.makedirs(analysis_notes_dir, exist_ok=True)

    baseline = retrieval_by_setting.get("fixed_256")
    proposed = retrieval_by_setting.get("structure_text_512")
    comparison_rows: List[Dict] = []
    if baseline and proposed:
        comparison_rows.append(
            {
                "metric": "hit_at_1",
                "baseline_fixed_256": f"{baseline['hit_at_1']:.6f}",
                "proposed_structure_text_512": f"{proposed['hit_at_1']:.6f}",
                "delta": f"{(proposed['hit_at_1'] - baseline['hit_at_1']):.6f}",
            }
        )
        comparison_rows.append(
            {
                "metric": "hit_at_5",
                "baseline_fixed_256": f"{baseline['hit_at_5']:.6f}",
                "proposed_structure_text_512": f"{proposed['hit_at_5']:.6f}",
                "delta": f"{(proposed['hit_at_5'] - baseline['hit_at_5']):.6f}",
            }
        )
        comparison_rows.append(
            {
                "metric": "mrr",
                "baseline_fixed_256": f"{baseline['mrr']:.6f}",
                "proposed_structure_text_512": f"{proposed['mrr']:.6f}",
                "delta": f"{(proposed['mrr'] - baseline['mrr']):.6f}",
            }
        )
        comparison_rows.append(
            {
                "metric": "ndcg_at_10",
                "baseline_fixed_256": f"{baseline['ndcg_at_10']:.6f}",
                "proposed_structure_text_512": f"{proposed['ndcg_at_10']:.6f}",
                "delta": f"{(proposed['ndcg_at_10'] - baseline['ndcg_at_10']):.6f}",
            }
        )

    _write_csv(
        os.path.join(tables_dir, "text_baseline_vs_proposed.csv"),
        comparison_rows,
        ["metric", "baseline_fixed_256", "proposed_structure_text_512", "delta"],
    )

    sensitivity_rows: List[Dict] = []
    for setting, values in sorted(retrieval_by_setting.items()):
        if not (setting.startswith("fixed_") or setting.startswith("structure_text_")):
            continue
        sensitivity_rows.append(
            {
                "setting": setting,
                "mode": "structure_text" if setting.startswith("structure_text_") else "fixed",
                "chunk_size": _parse_chunk_size(setting),
                "mrr": f"{values['mrr']:.6f}",
                "hit_at_5": f"{values['hit_at_5']:.6f}",
            }
        )

    sensitivity_rows = sorted(sensitivity_rows, key=lambda r: (r["mode"], r["chunk_size"]))
    _write_csv(
        os.path.join(tables_dir, "text_chunk_sensitivity.csv"),
        sensitivity_rows,
        ["setting", "mode", "chunk_size", "mrr", "hit_at_5"],
    )

    failure_counter: Dict[Tuple[str, str], int] = defaultdict(int)
    detail_paths = sorted(glob.glob(args.retrieval_details_glob))
    for path in detail_paths:
        setting = _normalize_setting(os.path.basename(path).replace(".json", ""))
        if setting not in {"fixed_256", "structure_text_512"}:
            continue
        details = _load_json(path).get("details", [])
        for d in details:
            if d.get("hit"):
                continue
            query_type = d.get("query_type") or "UNKNOWN"
            failure_counter[(setting, query_type)] += 1

    failure_rows: List[Dict] = []
    for (setting, query_type), count in sorted(failure_counter.items()):
        failure_rows.append({"setting": setting, "query_type": query_type, "failure_count": count})

    _write_csv(
        os.path.join(tables_dir, "text_failure_cases_by_type.csv"),
        failure_rows,
        ["setting", "query_type", "failure_count"],
    )

    with open(failure_notes_out, "w", encoding="utf-8") as f:
        f.write("# Text Failure Notes\n\n")
        f.write("## Baseline vs Proposed\n")
        if baseline and proposed:
            f.write(
                f"- baseline(`fixed_256`) MRR={baseline['mrr']:.4f}, proposed(`structure_text_512`) MRR={proposed['mrr']:.4f}\n"
            )
            f.write(f"- MRR delta: {proposed['mrr'] - baseline['mrr']:+.4f}\n")
        f.write("\n## Failure by Query Type\n")
        if not failure_rows:
            f.write("- no failure detail files found\n")
        else:
            for row in failure_rows:
                f.write(
                    f"- {row['setting']} | {row['query_type']} | failures={row['failure_count']}\n"
                )

    def _bar(v: float, width: int = 24) -> str:
        filled = max(0, min(width, int(round(v * width))))
        return "█" * filled + "░" * (width - filled)

    with open(os.path.join(figures_dir, "text_chunk_size_vs_mrr.md"), "w", encoding="utf-8") as f:
        f.write("# Chunk Size vs MRR (ASCII)\n\n")
        for row in sensitivity_rows:
            mode = row["mode"]
            size = row["chunk_size"]
            mrr = float(row["mrr"])
            f.write(f"- {mode}_{size:>3}: {_bar(mrr)} {mrr:.4f}\n")

    with open(os.path.join(figures_dir, "text_mode_comparison.md"), "w", encoding="utf-8") as f:
        f.write("# Mode Comparison (fixed vs structure_text)\n\n")
        if baseline and proposed:
            f.write(f"- fixed_256 MRR: {baseline['mrr']:.4f}\n")
            f.write(f"- structure_text_512 MRR: {proposed['mrr']:.4f}\n")
            f.write(f"- delta: {proposed['mrr'] - baseline['mrr']:+.4f}\n")

    with open(analysis_notes_out, "w", encoding="utf-8") as f:
        f.write("# Analysis Notes\n\n")
        f.write("## Text Track\n")
        if baseline and proposed:
            f.write(
                f"- baseline(`fixed_256`) 대비 proposed(`structure_text_512`)가 MRR에서 {proposed['mrr'] - baseline['mrr']:+.4f} 개선\n"
            )
        best = max(retrieval_by_setting.items(), key=lambda x: x[1]["mrr"]) if retrieval_by_setting else None
        if best:
            f.write(f"- 최고 MRR setting: `{best[0]}` ({best[1]['mrr']:.4f})\n")
        f.write(f"- 작은 chunk 민감도는 `{os.path.join(tables_dir, 'text_chunk_sensitivity.csv')}` 참조\n")
        f.write(f"- 실패 유형 분포는 `{os.path.join(tables_dir, 'text_failure_cases_by_type.csv')}` 참조\n")

    print(f"[DONE] wrote {args.out_metrics}")
    print(f"[DONE] wrote {markdown_summary_out}")
    print(f"[DONE] wrote {full_markdown_out}")
    print(f"[DONE] wrote {failure_notes_out}")
    print(f"[DONE] wrote {tables_dir}/text_*.csv")
    print(f"[DONE] wrote {figures_dir}/text_*.md")
    print(f"[DONE] wrote {analysis_notes_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
