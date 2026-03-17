# Text Experiment Cleanup Screening

기준 시점: 2026-03-16

## 요약

- 텍스트 실험의 현재 기준 경로는 `data/text/*`, `results/runs/<run_tag>/`, `vector_db/faiss_text_*`로 보임.
- 즉시 정리 후보 중 가장 큰 것은 다음 3종류다.
  - `data/raw/*`: `data/text/raw/*`와 내용이 완전히 동일한 중복 원본
  - 루트 `results/text_*`: 최신 run 구조(`results/runs/text_benchmark_20260315_en/`)와 병행 저장된 레거시 산출물
  - 파이썬 캐시 디렉터리: `__pycache__/`
- 다만 `data/processed/*`, `vector_db/faiss.index`, `vector_db/faiss_fixed.index` 등은 아직 레거시 문서/스크립트에서 참조하므로 바로 삭제보다는 "레거시 정리 단계"로 미루는 편이 안전하다.

## 관찰

### 1. 원본 텍스트 중복

`data/raw/*`와 `data/text/raw/*`는 SHA-256 기준으로 모두 동일했다.

- 예: `data/raw/Book1.txt` == `data/text/raw/Book1.txt`
- 예: `data/raw/hp_spells_list.txt` == `data/text/raw/hp_spells_list.txt`

용량:

- `data/raw`: 약 11M
- `data/text/raw`: 약 6.9M

권장:

- 텍스트 트랙 기준 경로가 `data/text/raw`로 굳었다면 `data/raw/*`는 정리 후보
- 단, `fetch_imdb.py`, `fetch_imdb2.py`, `len.py`, 일부 온보딩 문서는 아직 `data/raw`를 언급하므로 삭제 전 참조 정리가 필요

### 2. 결과물 구조 이원화

현재 문서상 최신 보존 위치:

- `results/runs/text_benchmark_20260315_en/`

루트 `results/`에는 아래 레거시 산출물이 남아 있다.

- retrieval JSON: `results/text_e*.json`, `results/text_e*_q30.json`
- generation JSON: `results/text_generation_*.json`
- 집계물: `results/text_metrics.csv`, `results/text_structure_metrics.json`
- 정답 채점: `results/text_answer_correctness_*.csv`
- 요약 문서: `results/text_q30_experiment_report.md`, `results/text_failure_notes.md`
- 표/도해 일부는 `results/tables`, `results/figures`에도 별도로 존재

권장:

- 최신 run 디렉터리가 canonical이면 루트 `results/text_*`는 1차 archive 또는 삭제 후보
- 다만 `scripts/build_text_analysis_artifacts.py`, `scripts/eval_answer_correctness.py`, `scripts/run_text_generation_all.py`의 기본 인자가 아직 루트 `results/`를 향함

### 3. 대용량 재생성 산출물

용량 기준 큰 항목:

- `vector_db`: 약 1.1G
- `data/text/processed`: 약 547M
- `data/processed`: 약 117M

현재 텍스트 실험과 직접 연결된 것은 주로 아래다.

- `data/text/processed/chunks_fixed_{64,128,256,512}*.json`
- `data/text/processed/chunks_structure_text_{64,128,256,512}*.json`
- `data/text/processed/chunks_token_256*.json`
- `vector_db/faiss_text_*`

보류가 필요한 레거시 산출물:

- `data/processed/chunks.json`
- `data/processed/chunks_fixed.json`
- `data/processed/chunks_structure_text.json`
- `data/processed/chunks_structure_text_injected.json`
- `data/processed/chunks_structure_code.json`
- `vector_db/faiss.index`
- `vector_db/faiss_fixed.index`
- `vector_db/faiss_structure_text.index`
- `vector_db/faiss_structure_text_injected.index`

이 파일들은 재생성 가능하지만, 아직 `config.py`, `RAG_PIPELINE.md`, `COURSE_ONBOARDING.md`, `POD_SPLIT_ONBOARDING.md`, 일부 스크립트가 레거시 경로를 같이 참조한다.

### 4. 명확한 캐시/환경성 파일

즉시 정리해도 무방한 범주:

- `.venv_selee/` 자체는 가상환경이므로 저장소 관점에서는 불필요
- `__pycache__/`
- `scripts/__pycache__/`
- `rag_pipeline/__pycache__/`
- `ingest/__pycache__/`

용량:

- `.venv_selee`: 약 7.7G
- 파이썬 캐시 합계: 수십 KB 수준

주의:

- `.venv_selee/` 삭제는 개발 환경을 다시 세팅해야 할 수 있으므로, "프로젝트에서 불필요"와 "지금 지워도 됨"은 다르다.

## 추천 정리 단계

### Phase 1. 바로 해도 안전한 후보

- `__pycache__/`
- `scripts/__pycache__/`
- `rag_pipeline/__pycache__/`
- `ingest/__pycache__/`
- 루트 `results/text_*`
- `results/tables/*`
- `results/figures/*`

전제:

- 최신 보고/재현 기준을 `results/runs/text_benchmark_20260315_en/`로 통일할 때

### Phase 2. 중복 데이터 정리 후보

- `data/raw/*`

전제:

- 텍스트 트랙 입력을 `data/text/raw/*`로 완전히 통일할 때
- `scripts/fetch_imdb.py`, `scripts/fetch_imdb2.py`, `scripts/len.py`, 온보딩 문서의 레거시 언급을 먼저 정리할 때

### Phase 3. 레거시 파이프라인 철수 후 정리 후보

- `data/processed/*`
- `vector_db/faiss.index`
- `vector_db/faiss_fixed.index`
- `vector_db/faiss_structure_text.index`
- `vector_db/faiss_structure_text_injected.index`

전제:

- `config.py`와 문서를 텍스트 실험 기준 경로로 통일
- 레거시 데모/온보딩 문서에서 해당 경로 제거

### Phase 4. 환경 자체 정리

- `.venv_selee/`

전제:

- 현재 작업에 이 가상환경이 더 이상 필요 없을 때
- 새 환경 재구성이 가능할 때

## 지금 기준 추천 액션

가장 무난한 첫 정리는 아래다.

1. 루트 `results/`의 텍스트 실험 산출물을 run 디렉터리 기준으로 정리
2. 파이썬 캐시 디렉터리 삭제
3. 레거시 참조를 정리한 뒤 `data/raw/*` 제거
4. 마지막으로 레거시 `data/processed/*`, `vector_db/faiss*.index` 정리 여부 판단

## 참고 참조처

- 현재 텍스트 실험 기준 문서: `TEXT_EXPERIMENTS.md`
- 현재 최신 run: `results/runs/text_benchmark_20260315_en/`
- 레거시 경로를 아직 참조하는 파일:
  - `config.py`
  - `RAG_PIPELINE.md`
  - `COURSE_ONBOARDING.md`
  - `POD_SPLIT_ONBOARDING.md`
  - `scripts/eval_detailed_report.py`
  - `scripts/inject_metadata.py`
  - `scripts/smoke_test_code.py`
