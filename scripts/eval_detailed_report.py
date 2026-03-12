"""
Generate a detailed evaluation report for Hybrid Retrieval.

Includes:
- Query list and count
- Retrieved sources
- Hit@K, MRR detail per query
- RRF contribution ratio (FAISS vs BM25)
- Optional model answer per query

Usage:
python3 scripts/eval_detailed_report.py \
  --mode fixed \
    --queries data/text/eval/queries_text_main.jsonl \
    --chunks data/text/processed/chunks_fixed_metadata.json \
  --index vector_db/faiss_fixed.index \
  --out-md results/detailed_eval_fixed.md \
  --out-json results/detailed_eval_fixed.json \
  --k 5 \
  --rrf-k 60 \
  --with-answer
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class RankedDoc:
    doc_id: str
    doc: Document
    rank: int
    source: str
    faiss_score: float
    bm25_score: float
    total_score: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detailed hybrid retrieval report")
    parser.add_argument("--mode", required=True, help="Mode label for report (e.g., fixed)")
    parser.add_argument("--queries", required=True, help="JSONL query file path")
    parser.add_argument("--chunks", required=True, help="Chunk metadata JSON path")
    parser.add_argument("--index", required=True, help="FAISS index path")
    parser.add_argument("--out-md", required=True, help="Output markdown report path")
    parser.add_argument("--out-json", required=True, help="Output json report path")
    parser.add_argument("--k", type=int, default=5, help="Top-K")
    parser.add_argument("--rrf-k", type=int, default=60, help="RRF constant")
    parser.add_argument(
        "--with-answer",
        action="store_true",
        help="Generate model answer per query (slow, loads EXAONE)",
    )
    return parser.parse_args()


def load_queries(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_documents(chunks_path: str) -> List[Document]:
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    docs: List[Document] = []
    for chunk in chunks:
        docs.append(
            Document(
                page_content=chunk.get("text", ""),
                metadata={
                    "source": chunk.get("source_file", "Unknown"),
                    "chunk_id": chunk.get("chunk_id", -1),
                },
            )
        )
    return docs


def build_vectorstore(index_path: str, docs: List[Document]) -> FAISS:
    index = faiss.read_index(index_path)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    index_to_docstore_id = {i: str(i) for i in range(len(docs))}
    docstore = InMemoryDocstore({str(i): doc for i, doc in enumerate(docs)})
    return FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id,
    )


def tokenize(text: str) -> List[str]:
    return text.lower().split()


def build_bm25(docs: List[Document]) -> BM25Okapi:
    tokenized = [tokenize(d.page_content) for d in docs]
    return BM25Okapi(tokenized)


def get_doc_id(doc: Document) -> str:
    return str(hash(doc.page_content))


def reciprocal_rank_fusion(
    faiss_docs: List[Document], bm25_docs: List[Document], rrf_k: int, top_k: int
) -> Tuple[List[RankedDoc], float, float]:
    score_map: Dict[str, Dict[str, Any]] = {}

    for rank, doc in enumerate(faiss_docs, start=1):
        doc_id = get_doc_id(doc)
        contrib = 1.0 / (rrf_k + rank)
        if doc_id not in score_map:
            score_map[doc_id] = {"doc": doc, "faiss": 0.0, "bm25": 0.0}
        score_map[doc_id]["faiss"] += contrib

    for rank, doc in enumerate(bm25_docs, start=1):
        doc_id = get_doc_id(doc)
        contrib = 1.0 / (rrf_k + rank)
        if doc_id not in score_map:
            score_map[doc_id] = {"doc": doc, "faiss": 0.0, "bm25": 0.0}
        score_map[doc_id]["bm25"] += contrib

    ranked: List[RankedDoc] = []
    for doc_id, payload in score_map.items():
        doc = payload["doc"]
        faiss_score = payload["faiss"]
        bm25_score = payload["bm25"]
        total = faiss_score + bm25_score
        ranked.append(
            RankedDoc(
                doc_id=doc_id,
                doc=doc,
                rank=0,
                source=doc.metadata.get("source", "Unknown"),
                faiss_score=faiss_score,
                bm25_score=bm25_score,
                total_score=total,
            )
        )

    ranked.sort(key=lambda x: x.total_score, reverse=True)
    ranked = ranked[:top_k]
    for i, item in enumerate(ranked, start=1):
        item.rank = i

    faiss_sum = float(np.sum([r.faiss_score for r in ranked])) if ranked else 0.0
    bm25_sum = float(np.sum([r.bm25_score for r in ranked])) if ranked else 0.0
    total_sum = faiss_sum + bm25_sum
    if total_sum == 0:
        return ranked, 0.0, 0.0
    return ranked, faiss_sum / total_sum, bm25_sum / total_sum


def maybe_build_answerer(with_answer: bool):
    if not with_answer:
        return None, None
    try:
        from rag_pipeline.prompt import build_prompt  # lazy import
        from rag_pipeline.rag_chain import rag_answer  # lazy import (loads model)
    except Exception as e:
        print(f"[WARN] Answer generation disabled due to load error: {e}")
        return None, None

    return build_prompt, rag_answer


def evaluate(args: argparse.Namespace) -> Dict[str, Any]:
    queries = load_queries(args.queries)
    docs = load_documents(args.chunks)
    vectorstore = build_vectorstore(args.index, docs)
    bm25 = build_bm25(docs)
    build_prompt, rag_answer = maybe_build_answerer(args.with_answer)

    evaluated = 0
    skipped = 0
    hit_count = 0
    mrr_sum = 0.0
    details: List[Dict[str, Any]] = []

    for row in queries:
        qid = row.get("qid", "unknown")
        query = row.get("query", "")
        gold_sources = row.get("gold_sources") or []

        faiss_docs = vectorstore.similarity_search(query, k=args.k)
        tokenized_query = tokenize(query)
        bm25_docs = bm25.get_top_n(tokenized_query, docs, n=args.k)
        ranked, faiss_ratio, bm25_ratio = reciprocal_rank_fusion(
            faiss_docs, bm25_docs, args.rrf_k, args.k
        )

        retrieved_sources = [r.source for r in ranked]

        rank = None
        rr = 0.0
        hit = False
        if gold_sources:
            evaluated += 1
            for i, src in enumerate(retrieved_sources, start=1):
                if src in gold_sources:
                    rank = i
                    break
            hit = rank is not None
            rr = 0.0 if rank is None else 1.0 / rank
            if hit:
                hit_count += 1
            mrr_sum += rr
        else:
            skipped += 1

        answer = None
        answer_error = None
        if args.with_answer and build_prompt and rag_answer:
            try:
                contexts = [r.doc.page_content for r in ranked]
                prompt = build_prompt(contexts, query)
                answer = rag_answer(prompt)
            except Exception as e:
                answer_error = str(e)

        details.append(
            {
                "qid": qid,
                "query": query,
                "gold_sources": gold_sources,
                "retrieved_sources": retrieved_sources,
                "hit": hit,
                "rank": rank,
                "reciprocal_rank": rr,
                "rrf_ratio": {"faiss": faiss_ratio, "bm25": bm25_ratio},
                "ranked_docs": [
                    {
                        "rank": r.rank,
                        "source": r.source,
                        "faiss_score": r.faiss_score,
                        "bm25_score": r.bm25_score,
                        "total_score": r.total_score,
                    }
                    for r in ranked
                ],
                "answer": answer,
                "answer_error": answer_error,
            }
        )

    metrics = {
        "mode": args.mode,
        "k": args.k,
        "rrf_k": args.rrf_k,
        "total_queries": len(queries),
        "evaluated_queries": evaluated,
        "skipped_queries": skipped,
        "hit_rate_at_k": 0.0 if evaluated == 0 else hit_count / evaluated,
        "mrr": 0.0 if evaluated == 0 else mrr_sum / evaluated,
    }
    return {"metrics": metrics, "details": details}


def write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_markdown(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    m = payload["metrics"]
    rows = payload["details"]

    lines: List[str] = []
    lines.append(f"# Detailed Eval Report ({m['mode']})")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- total_queries: {m['total_queries']}")
    lines.append(f"- evaluated_queries: {m['evaluated_queries']}")
    lines.append(f"- skipped_queries: {m['skipped_queries']}")
    lines.append(f"- HitRate@{m['k']}: {m['hit_rate_at_k']:.4f}")
    lines.append(f"- MRR: {m['mrr']:.4f}")
    lines.append(f"- rrf_k: {m['rrf_k']}")
    lines.append("")
    lines.append("## Query Details")
    for row in rows:
        lines.append(f"### {row['qid']}")
        lines.append(f"- query: {row['query']}")
        lines.append(f"- gold_sources: {row['gold_sources']}")
        lines.append(f"- retrieved_sources(top-{m['k']}): {row['retrieved_sources']}")
        lines.append(f"- hit: {row['hit']}")
        lines.append(f"- reciprocal_rank: {row['reciprocal_rank']}")
        lines.append(
            f"- rrf_ratio: faiss={row['rrf_ratio']['faiss']:.4f}, bm25={row['rrf_ratio']['bm25']:.4f}"
        )
        if row.get("answer") is not None:
            lines.append(f"- answer: {row['answer']}")
        elif row.get("answer_error"):
            lines.append(f"- answer_error: {row['answer_error']}")
        lines.append("- ranked_docs:")
        for d in row["ranked_docs"]:
            lines.append(
                f"  - rank={d['rank']}, source={d['source']}, "
                f"faiss={d['faiss_score']:.6f}, bm25={d['bm25_score']:.6f}, total={d['total_score']:.6f}"
            )
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    args = parse_args()
    payload = evaluate(args)
    write_json(args.out_json, payload)
    write_markdown(args.out_md, payload)
    print(f"[DONE] JSON: {args.out_json}")
    print(f"[DONE] MD: {args.out_md}")
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
