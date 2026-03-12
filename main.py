"""
Harry Potter RAG System - Main Execution Module
Professional Edition for Seminar
"""
import json
import os
import faiss
import argparse
import time
from config import FAISS_INDEX_PATH, LEGACY_PROCESSED_DIR, TEXT_PROCESSED_DIR
from rag_pipeline.hybrid_retriever import HybridRetriever
from rag_pipeline.prompt import build_prompt
from rag_pipeline.rag_chain import rag_answer

# LangChain imports for FAISS VectorStore wrapper
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.documents import Document

def print_boxed_response(text):
    """답변 내용을 깔끔한 테두리 박스에 담아 출력합니다."""
    lines = text.split('\n')
    # 터미널 너비에 맞춰 유동적으로 조절 (최대 80자)
    max_len = max(len(line) for line in lines) if lines else 0
    width = min(max_len, 80)
    
    border = "+" + "-" * (width + 4) + "+"
    print("\n" + border)
    print("| " + "FINAL AI RESPONSE".center(width + 2) + " |")
    print(border)
    for line in lines:
        # 긴 문장은 자르거나 그대로 출력 (데모용이므로 간단히 처리)
        print(f"|  {line.ljust(width)}  |")
    print(border + "\n")

def load_chunks_and_index():
    """청크 데이터와 FAISS 인덱스를 로드합니다."""
    processed_dirs = [TEXT_PROCESSED_DIR, LEGACY_PROCESSED_DIR]
    chunks_path = None

    env_chunks_path = os.getenv("CHUNKS_PATH")
    if env_chunks_path:
        chunks_path = env_chunks_path
    else:
        for directory in processed_dirs:
            metadata_path = os.path.join(directory, "chunks_metadata.json")
            base_path = os.path.join(directory, "chunks.json")
            if os.path.exists(metadata_path):
                chunks_path = metadata_path
                break
            if os.path.exists(base_path):
                chunks_path = base_path
                break
    
    if not chunks_path or not os.path.exists(chunks_path):
        print(f"[ERROR] Data file not found: {chunks_path}")
        return None, None
    
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    if not os.path.exists(FAISS_INDEX_PATH):
        print(f"[ERROR] FAISS index not found: {FAISS_INDEX_PATH}")
        return None, None
    
    index = faiss.read_index(FAISS_INDEX_PATH)
    return chunks, index

def main():
    parser = argparse.ArgumentParser(description="Harry Potter RAG System")
    parser.add_argument("--query", type=str, default="Tell me about Harry Potter", help="User Query")
    parser.add_argument("--filter", type=str, default=None, help="Metadata Filter (JSON)")
    parser.add_argument("--k", type=int, default=3, help="Number of chunks to retrieve")
    parser.add_argument("--chunks-path", type=str, default=None, help="Override chunks metadata/json path")
    args = parser.parse_args()

    if args.chunks_path:
        os.environ["CHUNKS_PATH"] = args.chunks_path

    print("[INFO] Initializing RAG System Components...")
    chunks, index = load_chunks_and_index()
    
    if chunks is None or index is None:
        return
    
    print(f"[INFO] Database: {len(chunks)} chunks loaded")
    print(f"[INFO] Index: FAISS loaded successfully\n")

    # Step 2: Convert chunks to LangChain Document objects
    print("[INFO] Converting chunks to Document objects...")
    documents = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk.get('text', ''),
            metadata={
                'source': chunk.get('source_file', 'Unknown'),
                'volume': chunk.get('volume', 'Unknown'),
                'chunk_id': chunk.get('chunk_id', -1)
            }
        )
        documents.append(doc)
    
    # Step 3: Wrap raw FAISS index with LangChain FAISS VectorStore
    print("[INFO] Initializing LangChain FAISS VectorStore wrapper...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Create index_to_docstore_id mapping
    index_to_docstore_id = {i: str(i) for i in range(len(documents))}
    
    # Create InMemoryDocstore with documents
    docstore = InMemoryDocstore({str(i): doc for i, doc in enumerate(documents)})
    
    # Wrap raw FAISS index
    vectorstore = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id
    )
    
    # Step 4: Initialize HybridRetriever
    print("[INFO] Initializing HybridRetriever (BM25 + FAISS with RRF)...")
    retriever = HybridRetriever(
        vectorstore=vectorstore,
        docs=documents,
        k=60,  # RRF constant
        top_k=args.k
    )
    print("[INFO] HybridRetriever initialized successfully\n")

    metadata_filter = None
    if args.filter:
        try:
            metadata_filter = json.loads(args.filter)
            print(f"[INFO] Metadata Filter Applied: {metadata_filter}")
        except json.JSONDecodeError:
            print(f"[WARN] Invalid filter format: {args.filter}")

    # 1. 검색 단계 (Retrieval)
    print(f"[QUERY] {args.query}")
    print("[PROCESS] Searching for relevant document chunks (Hybrid Search: BM25 + Vector)...")
    
    start_search = time.perf_counter()
    retrieved_docs = retriever.invoke(args.query, metadata_filter=metadata_filter)
    end_search = time.perf_counter()
    
    # 2. 검색 결과 리포트
    print("-" * 60)
    print(f"[DEBUG] Hybrid Retrieval completed in {end_search - start_search:.4f}s")
    print("-" * 60)
    
    for i, doc in enumerate(retrieved_docs, 1):
        source = doc.metadata.get('source', 'Unknown')
        print(f"[{i}] Source: {source}")
        print(f"    Preview: {doc.page_content[:150]}...")

    # 3. 답변 생성 단계 (Generation)
    print("\n" + "=" * 60)
    print("  GENERATING RESPONSE VIA LOCAL LLM (EXAONE 3.5)")
    print("=" * 60)
    
    contexts = [doc.page_content for doc in retrieved_docs]
    prompt = build_prompt(contexts, args.query)
    
    # rag_answer 함수 내부에서 디버깅 로그가 찍힘
    answer = rag_answer(prompt)
    
    # 4. 박스 테두리 답변 출력
    print_boxed_response(answer)
    
    # 5. 출처 리스트 출력
    print("=" * 60)
    print("  REFERENCE LIST")
    print("=" * 60)
    sources = []
    for doc in retrieved_docs:
        info = doc.metadata.get('source', 'unknown')
        if info not in sources:
            sources.append(info)
    
    for i, source in enumerate(sources, 1):
        print(f"  {i}. {source}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()