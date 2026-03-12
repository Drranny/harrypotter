"""
벡터 DB 인덱싱 스크립트

이 스크립트는 청크 JSON 파일을 읽어서
메타데이터를 포함한 벡터 DB를 구축합니다.

사용법:
    python3 scripts/build_index.py
    python3 scripts/build_index.py --chunks-path data/text/processed/chunks_structure_text.json \
        --index-path vector_db/faiss_structure_text.index \
        --metadata-path data/text/processed/chunks_structure_text_metadata.json
"""
import os
import sys
import argparse

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import faiss
from ingest.embed import embed_chunks
from config import FAISS_INDEX_PATH, LEGACY_PROCESSED_DIR, TEXT_PROCESSED_DIR


def _first_existing_path(*candidates: str) -> str:
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def parse_args():
    processed_dir = _first_existing_path(TEXT_PROCESSED_DIR, LEGACY_PROCESSED_DIR)

    parser = argparse.ArgumentParser(description="Build FAISS index from chunk file")
    parser.add_argument(
        "--chunks-path",
        default=os.path.join(processed_dir, "chunks.json"),
        help="Input chunks JSON path",
    )
    parser.add_argument(
        "--index-path",
        default=FAISS_INDEX_PATH,
        help="Output FAISS index path",
    )
    parser.add_argument(
        "--metadata-path",
        default=os.path.join(processed_dir, "chunks_metadata.json"),
        help="Output metadata JSON path",
    )
    return parser.parse_args()


def build_vector_index(chunks_path: str, index_path: str, metadata_path: str):
    """
    chunks 파일을 읽어서 FAISS 인덱스를 구축합니다.
    """
    if not os.path.exists(chunks_path):
        print(f"❌ Error: {chunks_path} 파일이 없습니다.")
        print("   먼저 chunking 스크립트를 실행하세요.")
        return
    
    print(f"📖 Loading chunks from {chunks_path}...")
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    print(f"   총 {len(chunks)}개의 청크를 로드했습니다.")
    
    # 2. 텍스트만 추출하여 임베딩 생성
    print("\n🔢 Creating embeddings...")
    texts = [chunk["text"] for chunk in chunks]
    vectors = embed_chunks(texts)
    
    print(f"   임베딩 차원: {vectors.shape}")
    
    # 3. FAISS 인덱스 구축
    print("\n🗄️  Building FAISS index...")
    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    
    # 벡터를 float32로 변환 (FAISS 요구사항)
    vectors = vectors.astype('float32')
    index.add(vectors)
    
    # 4. 인덱스 저장
    index_dir = os.path.dirname(index_path)
    os.makedirs(index_dir, exist_ok=True)
    
    faiss.write_index(index, index_path)
    print(f"   ✅ 인덱스 저장 완료: {index_path}")
    
    # 5. 청크 메타데이터도 함께 저장 (검색 시 사용)
    metadata_dir = os.path.dirname(metadata_path)
    if metadata_dir:
        os.makedirs(metadata_dir, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 메타데이터 저장 완료: {metadata_path}")
    
    print(f"\n✨ 총 {len(chunks)}개의 청크가 인덱싱되었습니다!")
    print(f"   이제 index/metadata 경로를 사용해 검색을 실행할 수 있습니다.")

if __name__ == "__main__":
    args = parse_args()
    build_vector_index(
        chunks_path=args.chunks_path,
        index_path=args.index_path,
        metadata_path=args.metadata_path,
    )
