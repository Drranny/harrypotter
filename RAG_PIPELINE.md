# RAG 파이프라인 실행/운영 가이드

본 문서는 실행 방법, 실험 모드, 협업 시 고정 규칙을 한 곳에 모은 문서입니다.

## 1. 파이프라인 개요
- 데이터 준비: `data/text/raw`(텍스트), `data/raw_code`(코드, 선택)
- 전처리: `scripts/chunk_papers.py` 또는 `scripts/chunk_dataset.py`
- 색인: `scripts/build_index.py`
- 질의 실행: `main.py` (Hybrid Retriever + EXAONE)

## 2. 표준 실행 명령
```bash
# 1) 기본 전처리 (기존 호환)
python3 scripts/chunk_papers.py

# 2) 실험 모드 전처리
python3 scripts/chunk_dataset.py --mode fixed --output data/text/processed/chunks_fixed.json
python3 scripts/chunk_dataset.py --mode structure_text --output data/text/processed/chunks_structure_text.json
python3 scripts/chunk_dataset.py --mode structure_code --output data/text/processed/chunks_structure_code.json

# 3) 인덱스 구축
python3 scripts/build_index.py

# 4) 질의 실행
python3 main.py --query "Who is Dudley?" --k 3
```

## 3. 모드별 인덱스(실험용)
```bash
python3 scripts/build_index.py \
  --chunks-path data/text/processed/chunks_fixed.json \
  --index-path vector_db/faiss_fixed.index \
  --metadata-path data/text/processed/chunks_fixed_metadata.json

python3 scripts/build_index.py \
  --chunks-path data/text/processed/chunks_structure_text.json \
  --index-path vector_db/faiss_structure_text.index \
  --metadata-path data/text/processed/chunks_structure_text_metadata.json
```

## 4. 질의 실행(필터 포함)
```bash
# 기본 질의
python3 main.py --query "Who is Dudley?" --k 3

# 메타데이터 필터 적용
python3 main.py \
  --query "해리와 더즐리 가족 관계 알려줘" \
  --k 3 \
  --filter '{"source": "Book5.txt"}'
```

## 5. 평가 실행
```bash
# 1) 간단 지표 평가 (HitRate@K, MRR)
python3 scripts/eval_retrieval.py \
  --queries data/text/eval/queries_text_main.jsonl \
  --chunks data/text/processed/chunks_fixed_metadata.json \
  --index vector_db/faiss_fixed.index \
  --k 5 \
  --out results/text_fixed_metrics.json

# 2) 상세 리포트 평가 (쿼리/세부점수/RRF 비율/답변 필드)
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
```

## 6. 데이터/산출물 경로
- 텍스트 입력: `data/text/raw`
- 코드 입력(선택): `data/raw_code` (`.py`)
- 기본 청크: `data/text/processed/chunks.json`
- 실험 청크: `data/text/processed/chunks_<mode>.json`
- 기본 인덱스: `vector_db/faiss.index`
- 평가 질의셋:
  - `data/text/eval/queries_text_main.jsonl`
  - `data/eval/queries_code.jsonl`
- 평가 결과:
  - `results/*.json`
  - `results/*.md`

## 7. 실험 모드 정의
- `fixed`: 고정 길이 문자 분할
- `line`: 줄 단위 분할
- `token`: 공백 토큰 기준 분할
- `structure_text`: 문단/챕터 경계 기반 분할
- `structure_code`: AST 기반(`class`/`def`/제어 블록) 분할

## 8. 청크 스키마 최소 필수값
아래 필드는 항상 포함해야 인덱싱/검색 호환이 유지됩니다.
- `text`
- `source_file`
- `chunk_id`

## 9. 고정 기본 파라미터
- `chunk_size=500`
- `overlap=50`
- `top_k=5`
- `rrf_k=60`
- embedding model: `sentence-transformers/all-MiniLM-L6-v2`

## 10. 협업 규칙
- 실행 명령은 `python3`로 통일
- 기존 진입점 `scripts/chunk_papers.py` 동작을 깨지 않음
- 코드 데이터셋이 없어도 파이프라인은 실패하지 않고 종료
- 실행 규칙이 바뀌면 이 파일 먼저 갱신

## 11. 트러블슈팅
- `python: command not found`:
  - `python3` 사용
- `No module named rank_bm25`:
  - `pip install rank-bm25` 또는 `python3 -m pip install --user rank-bm25`
- `No module named langchain_community`:
  - `pip install langchain-community` 또는 `python3 -m pip install --user langchain-community`
- 코드 데이터셋 미존재 경고:
  - `structure_code` 모드에서 정상 동작(빈 출력 생성)

## 12. 최신 텍스트 실험 run
- latest run tag: `text_benchmark_20260315_en`
- run root: `results/runs/text_benchmark_20260315_en/`
- integrated metrics: `results/runs/text_benchmark_20260315_en/text_metrics.csv`
- correctness summary: `results/runs/text_benchmark_20260315_en/text_answer_correctness_summary.csv`
- presentation table: `results/runs/text_benchmark_20260315_en/tables/text_metrics_summary.md`
- full metrics table: `results/runs/text_benchmark_20260315_en/tables/text_metrics_full_summary.md`
