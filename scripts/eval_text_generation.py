#!/usr/bin/env python3
"""
Evaluate text generation metrics for RAG outputs.

Metrics:
- Answer Relevance: cosine(query, answer)
- Faithfulness: fraction of answer sentences supported by retrieved contexts

This script supports two answer modes:
- extractive (fast): compose answer from top retrieved chunks
- llm (slow): use the same build_prompt -> rag_answer path as question.py
"""

import argparse
import json
import math
import os
import re
import sys
import time
from typing import Dict, List, Tuple

import faiss
from rank_bm25 import BM25Okapi

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest.embed import model
from rag_pipeline.prompt import build_prompt
from rag_pipeline.retriever import retrieve


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate generation metrics on text queries")
    parser.add_argument("--queries", required=True, help="Query JSONL path")
    parser.add_argument("--chunks", required=True, help="Chunk metadata JSON path")
    parser.add_argument("--index", required=True, help="FAISS index path")
    parser.add_argument("--k", type=int, default=5, help="Top-K retrieval")
    parser.add_argument(
        "--answer-mode",
        choices=["extractive", "llm"],
        default="extractive",
        help="Answer generation mode",
    )
    parser.add_argument("--max-queries", type=int, default=0, help="Limit number of queries (0=all)")
    parser.add_argument("--support-threshold", type=float, default=0.35, help="Sentence support threshold")
    parser.add_argument("--answer-language", default="English", help="LLM answer language")
    parser.add_argument(
        "--save-full-transcript",
        action="store_true",
        help="Save CLI-like full transcript text (retrieval + debug + final answer) per query",
    )
    parser.add_argument("--out", required=True, help="Output JSON path")
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


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _split_sentences(text: str) -> List[str]:
    candidates = re.split(r"(?<=[.!?])\s+", text.strip())
    return [c.strip() for c in candidates if c and c.strip()]


def _extractive_answer(contexts: List[str], max_sentences: int = 3) -> str:
    selected: List[str] = []
    for ctx in contexts:
        for sentence in _split_sentences(ctx):
            sentence = sentence.strip()
            if sentence:
                selected.append(sentence)
            if len(selected) >= max_sentences:
                return " ".join(selected)
    return " ".join(selected)


def _answer_relevance(query: str, answer: str) -> float:
    vectors = model.encode([query, answer])
    return float(_cosine(vectors[0].tolist(), vectors[1].tolist()))


def _faithfulness(answer: str, contexts: List[str], threshold: float) -> float:
    sentences = _split_sentences(answer)
    if not sentences:
        return 0.0
    if not contexts:
        return 0.0

    sent_vecs = model.encode(sentences)
    ctx_vecs = model.encode(contexts)

    supported = 0
    for sent_vec in sent_vecs:
        max_sim = -1.0
        for ctx_vec in ctx_vecs:
            sim = _cosine(sent_vec.tolist(), ctx_vec.tolist())
            if sim > max_sim:
                max_sim = sim
        if max_sim >= threshold:
            supported += 1

    return supported / len(sentences)


def _load_answer_fn(mode: str):
    if mode == "llm":
        from rag_pipeline.rag_chain import generate_with_meta, rag_answer

        return generate_with_meta, rag_answer
    return None


def _build_transcript(
    query: str,
    answer: str,
    docs: List[Dict],
    generation_meta: Dict,
    setting: str,
) -> str:
    lines: List[str] = []
    lines.append("=" * 80)
    lines.append(f"📌 Query: {query}")
    lines.append(f"📊 Method: hybrid | Chunks: {setting}")
    lines.append("=" * 80)
    for i, doc in enumerate(docs, start=1):
        src = doc.get("source_file", "?")
        text = (doc.get("text", "") or "").replace("\n", " ")[:150]
        lines.append("")
        lines.append(f"[{i}] {src}")
        lines.append(f"    {text}...")
    lines.append("\n" + "=" * 80)
    lines.append("\n\n🤖 Generating answer from LG AI EXAONE...\n")
    lines.append("\n" + "-" * 60)
    lines.append(f"[DEBUG] Prompt Token Count: {generation_meta.get('prompt_token_count', 0)}")
    lines.append("[DEBUG] Local Inference in Progress...")
    lines.append("-" * 60)
    lines.append(f"[DEBUG] Latency: {generation_meta.get('latency_sec', 0.0):.2f}s")
    lines.append(
        f"[DEBUG] Throughput: {generation_meta.get('throughput_tokens_per_sec', 0.0):.2f} tokens/s"
    )
    lines.append(f"[DEBUG] Response Token Count: {generation_meta.get('response_token_count', 0)}")
    lines.append("-" * 60 + "\n")
    lines.append("\n" + "=" * 80)
    lines.append("✨ FINAL ANSWER")
    lines.append("=" * 80)
    lines.append(answer)
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    queries = load_jsonl(args.queries)

    if args.max_queries > 0:
        queries = queries[: args.max_queries]

    with open(args.chunks, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    index = faiss.read_index(args.index)
    bm25 = BM25Okapi([chunk.get("text", "").split() for chunk in chunks])

    answer_fns = _load_answer_fn(args.answer_mode)

    details: List[Dict] = []
    relevance_sum = 0.0
    faithfulness_sum = 0.0

    start = time.perf_counter()
    for idx, row in enumerate(queries, start=1):
        query = row.get("query", "")
        qid = row.get("qid") or row.get("query_id") or f"q_{idx}"

        docs = retrieve(query, index, chunks, k=args.k, bm25=bm25)
        contexts = [d.get("text", "") for d in docs]

        generation_meta: Dict = {}
        if args.answer_mode == "llm" and answer_fns is not None:
            generate_with_meta, _ = answer_fns
            prompt = build_prompt(contexts, query, answer_language=args.answer_language)
            generation_meta = generate_with_meta(prompt, answer_language=args.answer_language)
            answer = generation_meta.get("response", "")
        else:
            answer = _extractive_answer(contexts)

        ar = _answer_relevance(query, answer)
        faith = _faithfulness(answer, contexts, threshold=args.support_threshold)
        relevance_sum += ar
        faithfulness_sum += faith

        setting = os.path.basename(args.chunks).replace("chunks_", "").replace("_metadata.json", "")
        transcript = None
        if args.save_full_transcript and args.answer_mode == "llm":
            transcript = _build_transcript(query, answer, docs, generation_meta, setting)

        details.append(
            {
                "qid": qid,
                "query": query,
                "query_type": row.get("query_type") or row.get("type"),
                "answer_mode": args.answer_mode,
                "answer_relevance": ar,
                "faithfulness": faith,
                "retrieved_sources": [d.get("source_file", "Unknown") for d in docs],
                "retrieved_docs": [
                    {
                        "rank": rank,
                        "source_file": d.get("source_file", "Unknown"),
                        "preview": (d.get("text", "") or "").replace("\n", " ")[:150],
                    }
                    for rank, d in enumerate(docs, start=1)
                ],
                "answer_full": answer,
                "answer_preview": answer[:300],
                "generation": generation_meta,
                "full_transcript": transcript,
            }
        )

        print(f"[{idx}/{len(queries)}] {qid}: relevance={ar:.4f}, faithfulness={faith:.4f}")

    elapsed = time.perf_counter() - start
    n = len(details)
    metrics = {
        "queries": n,
        "k": args.k,
        "answer_mode": args.answer_mode,
        "answer_language": args.answer_language,
        "support_threshold": args.support_threshold,
        "answer_relevance": 0.0 if n == 0 else relevance_sum / n,
        "faithfulness": 0.0 if n == 0 else faithfulness_sum / n,
        "elapsed_sec": elapsed,
    }

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "details": details}, f, ensure_ascii=False, indent=2)

    print(f"[DONE] output={args.out}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
