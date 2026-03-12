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
python3 scripts/run_text_experiments.py --run e1
```
- mode: `fixed`, `token`, `structure_text`
- chunk size: `256`
- metric: `Hit@5`, `MRR`

## E2 Chunk size sweep (핵심)
```bash
python3 scripts/run_text_experiments.py --run e2
```
- mode: `fixed`, `structure_text`
- chunk size: `64`, `128`, `256`, `512`
- metric: `Hit@5`, `MRR`

## E3 Generation experiment (manual run)
```bash
python3 main.py --query "Why does Snape protect Harry?" --k 5
```
- retrieval 결과를 바탕으로 생성 품질 비교
- 실험 시 동일 query set으로 mode/chunk size만 바꿔 비교

## E4 Metadata ablation
```bash
# with metadata: metadata 주입 파일을 chunks로 사용
python3 scripts/inject_metadata.py \
  --input data/text/processed/chunks_structure_text_256.json \
  --output data/text/processed/chunks_structure_text_256_injected.json
```
이후 `build_index.py` + `eval_retrieval.py`를 동일하게 실행하여
`with / without` 결과를 비교합니다.

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
