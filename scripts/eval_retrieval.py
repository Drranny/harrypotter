"""
Retrieval evaluation script for HitRate@K, MRR, and nDCG@K.

Usage:
    python3 scripts/eval_retrieval.py \
    --queries data/text/eval/queries_text_main.jsonl \
    --chunks data/text/processed/chunks_fixed_metadata.json \
      --index vector_db/faiss_fixed.index \
      --k 5 \
    --ndcg-k 10 \
      --out results/text_fixed_metrics.json
"""

import argparse
import json
import math
import os
import sys
from typing import Dict, List, Tuple
import re

import faiss
from rank_bm25 import BM25Okapi

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline.retriever import retrieve


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval metrics")
    parser.add_argument("--queries", required=True, help="JSONL query file path")
    parser.add_argument("--chunks", required=True, help="Chunk metadata JSON path")
    parser.add_argument("--index", required=True, help="FAISS index path")
    parser.add_argument("--k", type=int, default=5, help="Top-K")
    parser.add_argument("--ndcg-k", type=int, default=10, help="Cutoff K for nDCG@K")
    parser.add_argument("--out", required=True, help="Output metrics JSON path")
    return parser.parse_args()


def load_queries(path: str) -> List[Dict]:
    queries: List[Dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))
    return queries


def load_chunks(chunks_path: str) -> List[Dict]:
    with open(chunks_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_to_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _chunk_key(chunk: Dict) -> str:
    paragraph_id = chunk.get("paragraph_id")
    if paragraph_id:
        return str(paragraph_id)
    source_file = chunk.get("source_file", "Unknown")
    chunk_id = chunk.get("chunk_id", -1)
    return f"{source_file}::chunk_{chunk_id}"


def _is_relevant(chunk: Dict, gold_sources: List[str], 
                 gold_symbols: List[str], gold_chunk_ids: List[str]) -> bool:

    # 1순위: chunk_id 직접 매칭
    if gold_chunk_ids and _chunk_key(chunk) in gold_chunk_ids:
        return True

    # 2순위: symbol 매칭
    if gold_symbols:
            chunk_text = chunk.get("text", "")
            chunk_parent = chunk.get("metadata", {}).get("parent", "")
            
            for symbol in gold_symbols:
                if "." in symbol:
                    class_name, method_name = symbol.split(".", 1)
                    # parent 문자열 안에 "function:함수명"이 정확히 있는지 검사!
                    if class_name in chunk_parent and f"function:{method_name}" in chunk_parent:
                        return True
                else:
                    # 단어 경계 체크로 부분 매칭 방지 (클래스명 등)
                    pattern = r'\b' + re.escape(symbol) + r'\b'
                    if re.search(pattern, chunk_parent) or re.search(pattern, chunk_text):
                        return True
                        
            # symbol 기준이 있는데 못 찾았으면 무조건 오답
            return False

    # 3순위: gold_symbols가 없을 때만 파일명 매칭
    else:
        chunk_source = os.path.basename(chunk.get("source_file", ""))
        if gold_sources:
            for gold_src in gold_sources:
                if os.path.basename(gold_src) == chunk_source:
                    return True

    return False


def _ndcg_at_k(relevances: List[int], k: int) -> float:
    rel = relevances[:k]
    if not rel:
        return 0.0

    def dcg(vals: List[int]) -> float:
        score = 0.0
        for idx, v in enumerate(vals, start=1):
            if v <= 0:
                continue
            score += (2**v - 1) / math.log2(idx + 1)
        return score

    ideal = sorted(rel, reverse=True)
    idcg = dcg(ideal)
    if idcg == 0.0:
        return 0.0
    return dcg(rel) / idcg


def evaluate(
    queries: List[Dict],
    index: faiss.Index,
    chunks: List[Dict],
    k: int,
    ndcg_k: int,
    bm25_index: BM25Okapi,
) -> Tuple[Dict, List[Dict]]:
    evaluated = 0
    hit_count_at_1 = 0
    hit_count = 0
    mrr_sum = 0.0
    ndcg_sum = 0.0
    skipped = 0
    per_query: List[Dict] = []

    for q in queries:
        gold_sources = _normalize_to_list(q.get("gold_sources"))
        gold_chunk_ids = _normalize_to_list(q.get("gold_chunk_ids") or q.get("gold_paragraph_ids"))
        
        # 쿼리에서 gold_symbols 꺼내오기
        gold_symbols = _normalize_to_list(q.get("gold_symbols"))

        if not gold_sources and not gold_chunk_ids and not gold_symbols:
            skipped += 1
            continue

        evaluated += 1
        query = q["query"]
        qid = q.get("qid") or q.get("query_id") or f"q_{evaluated}"
        retrieved_chunks = retrieve(query, index, chunks, k=k, bm25=bm25_index)
        retrieved_sources = [c.get("source_file", "Unknown") for c in retrieved_chunks]
        retrieved_chunk_keys = [_chunk_key(c) for c in retrieved_chunks]

        rank = None
        relevances: List[int] = []
        for i, chunk in enumerate(retrieved_chunks, start=1):
            relevant = _is_relevant(chunk, gold_sources=gold_sources, gold_symbols=gold_symbols, gold_chunk_ids=gold_chunk_ids)
            relevances.append(1 if relevant else 0)
            if rank is None and relevant:
                rank = i

        hit = rank is not None
        rr = 0.0 if rank is None else 1.0 / rank
        ndcg = _ndcg_at_k(relevances, ndcg_k)

        if rank == 1:
            hit_count_at_1 += 1
        if hit:
            hit_count += 1
        mrr_sum += rr
        ndcg_sum += ndcg

        per_query.append(
            {
                "qid": qid,
                "query": query,
                "query_type": q.get("query_type") or q.get("type"),
                "difficulty": q.get("difficulty"),
                "gold_sources": gold_sources,
                "gold_symbols": gold_symbols,
                "gold_chunk_ids": gold_chunk_ids,
                "retrieved_sources": retrieved_sources,
                "retrieved_chunk_ids": retrieved_chunk_keys,
                "hit": hit,
                "reciprocal_rank": rr,
                "ndcg": ndcg,
            }
        )

    metrics = {
        "k": k,
        "ndcg_k": ndcg_k,
        "total_queries": len(queries),
        "evaluated_queries": evaluated,
        "skipped_queries": skipped,
        "hit_rate_at_1": 0.0 if evaluated == 0 else hit_count_at_1 / evaluated,
        "hit_rate_at_k": 0.0 if evaluated == 0 else hit_count / evaluated,
        "mrr": 0.0 if evaluated == 0 else mrr_sum / evaluated,
        "ndcg_at_k": 0.0 if evaluated == 0 else ndcg_sum / evaluated,
    }
    return metrics, per_query


def main() -> None:
    args = parse_args()
    queries = load_queries(args.queries)
    chunks = load_chunks(args.chunks)
    bm25_index = BM25Okapi([chunk["text"].split() for chunk in chunks])
    index = faiss.read_index(args.index)
    metrics, per_query = evaluate(queries, index, chunks, args.k, args.ndcg_k, bm25_index)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "details": per_query}, f, ensure_ascii=False, indent=2)

    print(f"[DONE] Saved metrics to {args.out}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
