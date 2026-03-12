"""
메타데이터 필터링을 사용한 검색 예시

사용법:
    python scripts/search_with_metadata.py
"""
import json
import os
import sys
import faiss

# 프로젝트 최상단 경로를 파이썬 모듈 검색 경로에 추가합니다.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rank_bm25 import BM25Okapi
from ingest.embed import embed_chunks
from rag_pipeline.retriever import retrieve
from config import FAISS_INDEX_PATH, LEGACY_PROCESSED_DIR, TEXT_PROCESSED_DIR


def _first_existing_path(*candidates: str) -> str:
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]

# 청크 로드
processed_dir = _first_existing_path(TEXT_PROCESSED_DIR, LEGACY_PROCESSED_DIR)
chunks_path = os.path.join(processed_dir, "chunks.json")
with open(chunks_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

# BM25 인덱스 초기화
bm25_index = BM25Okapi([chunk["text"].split() for chunk in chunks])

# FAISS 인덱스 로드
index = faiss.read_index(FAISS_INDEX_PATH)

# 예시 1: 리뷰만 검색
print("=" * 60)
print("예시 1: 리뷰만 검색")
print("=" * 60)
query = "What did critics say about the movie?"
review_chunks = retrieve(
    query,
    index,
    chunks,
    metadata_filter={"source": "review"},
    k=3,
    bm25=bm25_index,
)
print(f"검색 결과: {len(review_chunks)}개")
for i, chunk in enumerate(review_chunks, 1):
    print(f"\n[{i}] {chunk.get('source_file')} (type: {chunk.get('type')})")
    print(f"    {chunk['text'][:200]}...")

# 예시 2: 책 내용만 검색
print("\n" + "=" * 60)
print("예시 2: 책 내용만 검색 (1권)")
print("=" * 60)
query = "What happened in the first book?"
book_chunks = retrieve(
    query,
    index,
    chunks,
    metadata_filter={"source": "book", "volume": 1},
    k=3,
    bm25=bm25_index,
)
print(f"검색 결과: {len(book_chunks)}개")
for i, chunk in enumerate(book_chunks, 1):
    print(f"\n[{i}] {chunk.get('source_file')} (volume: {chunk.get('volume')})")
    print(f"    {chunk['text'][:200]}...")

# 예시 3: 로어(주문) 정보만 검색
print("\n" + "=" * 60)
print("예시 3: 주문 정보만 검색")
print("=" * 60)
query = "What spells are available?"
lore_chunks = retrieve(
    query,
    index,
    chunks,
    metadata_filter={"source": "lore", "topic": "spells"},
    k=3,
    bm25=bm25_index,
)
print(f"검색 결과: {len(lore_chunks)}개")
for i, chunk in enumerate(lore_chunks, 1):
    print(f"\n[{i}] {chunk.get('source_file')} (topic: {chunk.get('topic')})")
    print(f"    {chunk['text'][:200]}...")

# 예시 4: 캐릭터 정보만 검색
print("\n" + "=" * 60)
print("예시 4: 캐릭터 정보만 검색")
print("=" * 60)
query = "Tell me about Harry Potter character"
character_chunks = retrieve(
    query,
    index,
    chunks,
    metadata_filter={"source": "lore", "topic": "character"},
    k=3,
    bm25=bm25_index,
)
print(f"검색 결과: {len(character_chunks)}개")
for i, chunk in enumerate(character_chunks, 1):
    print(f"\n[{i}] {chunk.get('source_file')} (character: {chunk.get('character', 'unknown')})")
    print(f"    {chunk['text'][:200]}...")

# 예시 5: 필터 없이 전체 검색
print("\n" + "=" * 60)
print("예시 5: 필터 없이 전체 검색")
print("=" * 60)
query = "What is Harry Potter about?"
all_chunks = retrieve(query, index, chunks, k=3, bm25=bm25_index)
print(f"검색 결과: {len(all_chunks)}개")
for i, chunk in enumerate(all_chunks, 1):
    print(f"\n[{i}] {chunk.get('source_file')} (source: {chunk.get('source')})")
    print(f"    {chunk['text'][:200]}...")
