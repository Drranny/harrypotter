# Text Experiments (Harry Potter Only)

## Data layout (text track)

기존 경로(`data/raw`, `data/processed`, `data/eval`)도 유지되지만,
텍스트 실험은 위 `data/text/*`를 기본으로 사용합니다.

## Split policy (Harry Potter text track)
- `data/text/raw`: retrieval corpus 전체 본문
- `data/text/eval/queries_text_main.jsonl`: 빠른 반복 검증용 dev set
- `data/text/eval/queries_text_benchmark30.jsonl`: 비교/보고용 고정 benchmark test set
- `data/text/eval/queries_text_100_template.jsonl`: 확장 후보 pool (gold 확정 전 공식 평가 불가)
- 현재는 supervised fine-tuning용 train split을 따로 두지 않고, corpus/eval query 분리 기준으로 운영합니다.

## E1 Retrieval experiment
```bash
python3 scripts/run_text_experiments.py \
  --run e1 \
  --queries data/text/eval/queries_text_benchmark30.jsonl \
  --results-dir results/runs/<run_tag>/retrieval
```
- mode: `fixed`, `token`, `structure_text`
- chunk size: `256`
- retrieval: `Hit@1`, `Hit@5`, `MRR`, `nDCG@10`
- search pipeline: `hybrid` (FAISS + BM25 with RRF)

## E2 Chunk size sweep (핵심)
```bash
python3 scripts/run_text_experiments.py \
  --run e2 \
  --queries data/text/eval/queries_text_benchmark30.jsonl \
  --results-dir results/runs/<run_tag>/retrieval
```
- mode: `fixed`, `structure_text`
- chunk size: `64`, `128`, `256`, `512`
- retrieval: `Hit@1`, `Hit@5`, `MRR`, `nDCG@10`
- search pipeline: `hybrid` (FAISS + BM25 with RRF)

## E3 Generation experiment (manual run)
```bash
python3 question.py
```
- 인터랙티브 확인용
- retrieval method(`faiss`/`bm25`/`hybrid`), chunk setting, answer language(`English`/`Korean`) 선택 가능
- 논문용 자동 생성 평가는 아래 `E6` 또는 전체 파이프라인 스크립트를 사용

## E4 Metadata ablation
```bash
# with metadata: metadata 주입 파일을 chunks로 사용
python3 scripts/inject_metadata.py \
  --input data/text/processed/chunks_structure_text_256.json \
  --output data/text/processed/chunks_structure_text_256_injected.json
```
이후 `build_index.py` + `eval_retrieval.py`를 동일하게 실행하여
`with / without` 결과를 비교합니다.

## E5 Structure metric (Boundary Truncation Ratio)
```bash
python3 scripts/eval_text_structure_metrics.py \
  --chunks-glob "data/text/processed/chunks_*_metadata.json" \
  --only-modes "fixed,structure_text,token" \
  --out results/runs/<run_tag>/text_structure_metrics.json
```

## E6 Generation metric (Answer Relevance / Faithfulness)
```bash
# 논문용 LLM 평가(hybrid retrieval + EXAONE)
python3 scripts/eval_text_generation.py \
  --queries data/text/eval/queries_text_benchmark30.jsonl \
  --chunks data/text/processed/chunks_fixed_256_metadata.json \
  --index vector_db/faiss_text_fixed_256.index \
  --k 5 \
  --answer-mode llm \
  --save-full-transcript \
  --out results/runs/<run_tag>/generation/text_generation_fixed_256.json

python3 scripts/eval_text_generation.py \
  --queries data/text/eval/queries_text_benchmark30.jsonl \
  --chunks data/text/processed/chunks_structure_text_512_metadata.json \
  --index vector_db/faiss_text_structure_text_512.index \
  --k 5 \
  --answer-mode llm \
  --save-full-transcript \
  --out results/runs/<run_tag>/generation/text_generation_structure_text_512.json
```
- search pipeline: `hybrid` (FAISS + BM25 with RRF)
- generation pipeline: EXAONE LLM
- answer language: `English` (exact match / correctness evaluation alignment)
- saved fields: `answer_full`, `generation`, `full_transcript`

## E6-b Answer correctness
```bash
python3 scripts/eval_answer_correctness.py \
  --generation-glob "results/runs/<run_tag>/generation/text_generation_*.json" \
  --out-summary results/runs/<run_tag>/text_answer_correctness_summary.csv \
  --out-detailed results/runs/<run_tag>/text_answer_correctness_detailed.csv
```
- metric: `exact_match`, `fact_exact_match`, `entity_recall`, `fact_entity_recall`, `semantic_similarity`

## E7 Final aggregation (text_metrics.csv + analysis artifacts)
```bash
python3 scripts/build_text_analysis_artifacts.py \
  --retrieval-details-glob "results/runs/<run_tag>/retrieval/text_*.json" \
  --generation-glob "results/runs/<run_tag>/generation/text_generation_*.json" \
  --structure-metrics results/runs/<run_tag>/text_structure_metrics.json \
  --answer-correctness results/runs/<run_tag>/text_answer_correctness_summary.csv \
  --out-metrics results/runs/<run_tag>/text_metrics.csv \
  --tables-dir results/runs/<run_tag>/tables \
  --figures-dir results/runs/<run_tag>/figures \
  --analysis-notes-out results/runs/<run_tag>/analysis_notes.md
```

## Full pipeline (권장)
```bash
python3 scripts/run_text_full_pipeline.py --run-tag <run_tag>
```
- benchmark 30문항 기준 전체 파이프라인 실행
- 결과는 `results/runs/<run_tag>/` 아래에 보존
- 기본 비교 대상 9설정:
  - `fixed_64`, `fixed_128`, `fixed_256`, `fixed_512`
  - `token_256`
  - `structure_text_64`, `structure_text_128`, `structure_text_256`, `structure_text_512`

## Query set
- 빠른 검증: `data/text/eval/queries_text_main.jsonl`
- 논문 샘플 벤치마크(30): `data/text/eval/queries_text_benchmark30.jsonl`
- CSV 뷰: `data/text/eval/queries_text_benchmark30.csv`
- 논문용 템플릿: `data/text/eval/queries_text_100_template.jsonl`

주의: 100 템플릿은 `gold_sources`가 비어 있으므로
논문 실험 전 반드시 라벨링을 완료해야 Hit/MRR 계산이 가능합니다.

## Gold paragraph labeling
1) paragraph 코퍼스 생성
```bash
python3 scripts/build_paragraph_corpus.py \
  --input-dir data/text/raw \
  --output data/text/processed/paragraphs.json
```

2) benchmark query의 gold paragraph 후보 자동 추천
```bash
python3 scripts/suggest_gold_paragraphs.py \
  --queries data/text/eval/queries_text_benchmark30.jsonl \
  --paragraphs data/text/processed/paragraphs.json \
  --top-n 3 \
  --out data/text/eval/queries_text_benchmark30_suggested.jsonl
```

3) 사람이 `gold_paragraph_ids` 최종 확정

## Retrieval metric
- `Hit@1`
- `Hit@K`
- `MRR`
- `nDCG@K`

`scripts/eval_retrieval.py`는 `gold_sources`와 `gold_chunk_ids`(또는 `gold_paragraph_ids`)를 모두 지원합니다.

## Result layout
- `results/runs/<run_tag>/retrieval/`: 설정별 retrieval JSON
- `results/runs/<run_tag>/generation/`: 설정별 generation JSON (`answer_full`, `full_transcript` 포함)
- `results/runs/<run_tag>/text_structure_metrics.json`: 구조 지표
- `results/runs/<run_tag>/text_answer_correctness_summary.csv`: 정답 채점 요약
- `results/runs/<run_tag>/text_answer_correctness_detailed.csv`: 문항별 정답 채점
- `results/runs/<run_tag>/text_metrics.csv`: 통합 지표
- `results/runs/<run_tag>/tables/text_metrics_summary.md`: 발표용 마크다운 표

## Latest completed run
- run tag: `text_benchmark_20260315_en`
- root: `results/runs/text_benchmark_20260315_en/`
- integrated metrics: `results/runs/text_benchmark_20260315_en/text_metrics.csv`
- correctness summary: `results/runs/text_benchmark_20260315_en/text_answer_correctness_summary.csv`
- presentation table: `results/runs/text_benchmark_20260315_en/tables/text_metrics_summary.md`
- full metrics table: `results/runs/text_benchmark_20260315_en/tables/text_metrics_full_summary.md`
