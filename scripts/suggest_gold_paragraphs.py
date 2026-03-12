"""
Suggest gold paragraph IDs for benchmark queries using BM25 over paragraph corpus.

Usage:
    python3 scripts/suggest_gold_paragraphs.py \
      --queries data/text/eval/queries_text_benchmark30.jsonl \
      --paragraphs data/text/processed/paragraphs.json \
      --top-n 3 \
      --out data/text/eval/queries_text_benchmark30_suggested.jsonl
"""

import argparse
import json
import os
from typing import Dict, List

from rank_bm25 import BM25Okapi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Suggest gold paragraph labels")
    parser.add_argument("--queries", required=True, help="Input benchmark JSONL")
    parser.add_argument("--paragraphs", required=True, help="Paragraph corpus JSON")
    parser.add_argument("--top-n", type=int, default=3, help="Number of suggestions")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    return parser.parse_args()


def load_jsonl(path: str) -> List[Dict]:
    rows: List[Dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    args = parse_args()

    with open(args.paragraphs, "r", encoding="utf-8") as f:
        paragraphs: List[Dict] = json.load(f)

    queries = load_jsonl(args.queries)

    docs = [p.get("text", "") for p in paragraphs]
    bm25 = BM25Okapi([d.lower().split() for d in docs])

    out_rows: List[Dict] = []

    for q in queries:
        query = q.get("query", "")
        expected = q.get("expected_entity_or_paragraph", "")
        retrieval_text = f"{query} {expected}".strip().lower()
        tokens = retrieval_text.split()

        scores = bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: args.top_n]

        suggestions = []
        for idx in top_indices:
            p = paragraphs[idx]
            suggestions.append(
                {
                    "paragraph_id": p.get("paragraph_id"),
                    "source_file": p.get("source_file"),
                    "score": float(scores[idx]),
                    "preview": p.get("text", "")[:160],
                }
            )

        row = dict(q)
        if not row.get("gold_paragraph_ids"):
            row["gold_paragraph_ids"] = []
        row["suggested_gold_paragraphs"] = suggestions
        out_rows.append(row)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[DONE] queries={len(out_rows)} output={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
