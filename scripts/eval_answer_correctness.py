#!/usr/bin/env python3
"""
Evaluate answer correctness for generation outputs.

Inputs:
- benchmark queries CSV
- answer key CSV (ground truth answer)
- entity key CSV (short answer + key entities)
- generation result JSON files (results/text_generation_*.json)

Outputs:
- results/text_answer_correctness_summary.csv
- results/text_answer_correctness_detailed.csv
"""

import argparse
import csv
import glob
import json
import os
import re
import sys
import unicodedata
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest.embed import model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate exact/entity correctness of generated answers")
    parser.add_argument("--queries-csv", default="data/text/eval/queries_text_benchmark30.csv")
    parser.add_argument("--answer-key", default="data/text/eval/answers_text_benchmark30.csv")
    parser.add_argument("--entity-key", default="data/text/eval/answers_text_benchmark30_entities.csv")
    parser.add_argument("--generation-glob", default="results/text_generation_*.json")
    parser.add_argument("--out-summary", default="results/text_answer_correctness_summary.csv")
    parser.add_argument("--out-detailed", default="results/text_answer_correctness_detailed.csv")
    return parser.parse_args()


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.lower()
    text = re.sub(r"[^a-z0-9가-힣\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _contains(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    return _normalize(needle) in _normalize(haystack)


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _query_maps(query_rows: List[Dict[str, str]]) -> Tuple[Dict[str, int], Dict[int, str]]:
    query_to_id: Dict[str, int] = {}
    id_to_type: Dict[int, str] = {}
    for r in query_rows:
        qid = int(r["query_id"])
        query_to_id[_normalize(r["query"])] = qid
        id_to_type[qid] = r.get("query_type", "")
    return query_to_id, id_to_type


def _load_answer_keys(rows: List[Dict[str, str]]) -> Dict[int, str]:
    return {int(r["query_id"]): r["ground_truth_answer"] for r in rows}


def _load_entity_keys(rows: List[Dict[str, str]]) -> Dict[int, Dict[str, List[str] | str]]:
    out: Dict[int, Dict[str, List[str] | str]] = {}
    for r in rows:
        qid = int(r["query_id"])
        entities = [e.strip() for e in (r.get("key_entities", "") or "").split(";") if e.strip()]
        out[qid] = {
            "short_answer": r.get("short_answer", ""),
            "entities": entities,
        }
    return out


def _setting_from_path(path: str) -> str:
    name = os.path.basename(path)
    return name.replace("text_generation_", "").replace(".json", "")


def main() -> int:
    args = parse_args()

    queries = _read_csv(args.queries_csv)
    answer_rows = _read_csv(args.answer_key)
    entity_rows = _read_csv(args.entity_key)

    query_to_id, id_to_type = _query_maps(queries)
    answer_key = _load_answer_keys(answer_rows)
    entity_key = _load_entity_keys(entity_rows)

    detail_rows: List[Dict[str, str]] = []
    summary_rows: List[Dict[str, str]] = []

    for path in sorted(glob.glob(args.generation_glob)):
        setting = _setting_from_path(path)
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        details = payload.get("details", [])
        if not details:
            continue

        em_hits = 0
        fact_em_hits = 0
        fact_count = 0
        entity_recall_sum = 0.0
        fact_entity_recall_sum = 0.0
        semantic_sum = 0.0
        n = 0

        for d in details:
            query = d.get("query", "")
            answer = d.get("answer_full") or d.get("answer_preview", "")
            if not query:
                continue

            qid = query_to_id.get(_normalize(query))
            if qid is None:
                continue

            gt = answer_key.get(qid, "")
            entity_info = entity_key.get(qid, {"short_answer": "", "entities": []})
            short_answer = str(entity_info.get("short_answer", ""))
            entities = list(entity_info.get("entities", []))

            exact_match = _contains(answer, short_answer)
            if exact_match:
                em_hits += 1

            matched_entities = sum(1 for e in entities if _contains(answer, e))
            entity_recall = 0.0 if not entities else matched_entities / len(entities)
            entity_recall_sum += entity_recall

            if gt:
                vecs = model.encode([answer, gt])
                semantic = _cosine(vecs[0].tolist(), vecs[1].tolist())
            else:
                semantic = 0.0
            semantic_sum += semantic

            q_type = id_to_type.get(qid, "")
            if q_type == "FACT":
                fact_count += 1
                if exact_match:
                    fact_em_hits += 1
                fact_entity_recall_sum += entity_recall

            detail_rows.append(
                {
                    "setting": setting,
                    "query_id": str(qid),
                    "query_type": q_type,
                    "query": query,
                    "short_answer": short_answer,
                    "answer_preview": answer[:300],
                    "exact_match": "1" if exact_match else "0",
                    "entity_recall": f"{entity_recall:.6f}",
                    "semantic_similarity": f"{semantic:.6f}",
                }
            )
            n += 1

        if n == 0:
            continue

        summary_rows.append(
            {
                "setting": setting,
                "queries": str(n),
                "exact_match": f"{em_hits / n:.6f}",
                "fact_exact_match": f"{(fact_em_hits / fact_count) if fact_count else 0.0:.6f}",
                "entity_recall": f"{entity_recall_sum / n:.6f}",
                "fact_entity_recall": f"{(fact_entity_recall_sum / fact_count) if fact_count else 0.0:.6f}",
                "semantic_similarity": f"{semantic_sum / n:.6f}",
            }
        )

    os.makedirs(os.path.dirname(args.out_summary) or ".", exist_ok=True)
    with open(args.out_summary, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "setting",
                "queries",
                "exact_match",
                "fact_exact_match",
                "entity_recall",
                "fact_entity_recall",
                "semantic_similarity",
            ],
        )
        writer.writeheader()
        for row in sorted(summary_rows, key=lambda r: r["setting"]):
            writer.writerow(row)

    with open(args.out_detailed, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "setting",
                "query_id",
                "query_type",
                "query",
                "short_answer",
                "answer_preview",
                "exact_match",
                "entity_recall",
                "semantic_similarity",
            ],
        )
        writer.writeheader()
        for row in sorted(detail_rows, key=lambda r: (r["setting"], int(r["query_id"]))):
            writer.writerow(row)

    print(f"[DONE] summary={args.out_summary}")
    print(f"[DONE] detailed={args.out_detailed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
