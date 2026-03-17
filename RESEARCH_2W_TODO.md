# Structure-Aware Chunking 연구 2주 실행 계획

기준 문서: `route.pdf`  
기간: 2주 (14일)  
목표: 설계 수준에서 멈춘 연구를 실행 가능한 실험/결과 수준으로 완료
상태 갱신: 2026-03-16 (text_benchmark_20260315_en run 반영)

## 성공 기준 (2주 종료 시점)
- 텍스트/코드 도메인 모두에서 baseline 대비 구조 인식 청킹 실험 완료
- 핵심 지표 산출 완료: 
  - 1단계(검색): `HitRate@K`, `MRR`
  - 2단계(구조): `Boundary Truncation Ratio`, `Syntax Error Rate`, `Orphan Code Ratio`, `Executable Chunk Ratio`
  - 3단계(생성): RAGAS 기반 `Answer Relevance`, `Faithfulness`
- 재현 가능한 실험 스크립트 + 결과표/그래프 + 분석 노트 확보

## 운영 방식
- 공통 기반 작업을 먼저 고정하고, 이후 `텍스트 트랙`과 `코드 트랙`을 분리해서 병렬 관리
- 체크 기준은 "문서에 적혀 있음"이 아니라 "저장소 산출물로 확인 가능함"
- 상태 라벨:
  - 완료: 실제 파일/로그/스크립트 존재
  - 진행중: 부분 결과 또는 초안 존재
  - 미착수: 산출물/근거 없음

## 공통 기반 트랙

### A. 실험 스펙/규칙
- [ ] 실험 질문 3개 확정
  - [ ] Q1: 작은 chunk size에서 성능 저하를 구조 인식 청킹이 완화하는가?
  - [ ] Q2: 코드 도메인에서 구조 보존 지표가 유의미하게 개선되는가?
  - [ ] Q3: 동일 인덱스로 다중 태스크 재사용성이 올라가는가?
- [x] baseline/제안 기법 정의 문서화
  - [x] Baseline A: fixed-size
  - [x] Baseline B: line-based (코드), token/문장 기반(텍스트)
  - [x] Proposed: structure-aware
- [ ] 평가 지표 계산 규칙 고정
  - 진행중: 검색 지표(`HitRate@K`, `MRR`)와 실행 기본 파라미터는 반영됨
  - 미완료: 구조 지표/생성 지표 계산 규칙 문서화 필요
- [x] 산출물: `RAG_PIPELINE.md` 갱신 완료

### B. 공통 파이프라인
- [x] fixed-size chunker 파라미터화 (`size`, `overlap`)
- [x] line-based/token-based chunker 구현
- [x] chunk 메타데이터 공통 스키마 통일
- [x] Embedding 인덱스(FAISS) 빌드 자동화
- [x] BM25 인덱스 구성
- [x] RRF fusion 점수 계산 통합
- [x] chunking 방식별 동일 인터페이스로 검색 가능하게 정리
- [x] 산출물: `scripts/chunk_dataset.py`, `scripts/build_index.py`, `scripts/search_with_metadata.py`, `scripts/eval_retrieval.py`

### C. 공통 검증
- [x] 샘플 질의로 end-to-end 동작 검증
- [x] 성능/오류 로그 수집
- [x] 깨지는 케이스(파싱 실패, 빈 청크, 메타데이터 누락) 수정
- [x] 산출물: `results/smoke_report.md`

## 텍스트 트랙

### T1. 데이터셋/질의셋
 [x] 텍스트 데이터셋(Harry Potter) 학습/평가 분리 규칙 정의
  - 규칙 1: `data/text/raw` 전체는 retrieval corpus(검색 대상 본문)로 사용하고, 현재 별도 supervised train split은 두지 않음
  - 규칙 2: `data/text/eval/queries_text_main.jsonl`은 빠른 반복 검증용 dev 성격의 평가셋으로 사용
  - 규칙 3: `data/text/eval/queries_text_benchmark30.jsonl`은 비교/보고용 고정 benchmark test set으로 사용
  - 규칙 4: `data/text/eval/queries_text_100_template.jsonl`은 향후 확장용 query pool이며, gold 라벨 확정 전 공식 평가셋으로 사용하지 않음
  - 규칙 5: retrieval corpus와 evaluation query set은 파일 레벨로 분리 관리하며, 평가는 `gold_sources` 또는 `gold_paragraph_ids` 기준으로만 수행
  - 현재 상태: 메인 질의셋 + 30문항 벤치마크 + qrels 초안 확보
- [x] 평가셋 스키마/운영 README 정리
  - 산출물: `data/text/eval/README.md`
- [x] 텍스트 데이터 품질 점검 스크립트 추가
  - 산출물: `scripts/audit_text_data.py`
- [x] paragraph-level gold labeling용 코퍼스 생성 파이프라인 구축
  - 산출물: `scripts/build_paragraph_corpus.py`, `data/text/processed/paragraphs.json`
- [x] benchmark query용 gold paragraph 후보 자동 추천 파이프라인 구축
  - 산출물: `scripts/suggest_gold_paragraphs.py`, `data/text/eval/queries_text_benchmark30_suggested.jsonl`

### T2. 텍스트 구조 인식 청킹
- [x] 문단/챕터 경계 기반 청킹 구현
- [x] source/book/chapter metadata 보존
- [x] 작은 chunk size 조건에서도 문맥 유지 정책 추가
- [x] 산출물: `data/processed/chunks_structure_text.json`, `data/processed/chunks_structure_text_metadata.json`

### T3. 텍스트 본실험
- [x] chunk size 조건 2~3개로 baseline/proposed 일괄 실행
- [x] 검색 지표 산출 (`HitRate@K`, `MRR`)
- [x] 구조 지표 산출 (`Boundary Truncation Ratio`)
- [x] 생성 지표 산출 (`Answer Relevance`, `Faithfulness`)
- [x] 정답 기반 correctness 지표 산출 (`Exact Match`, `Entity Recall`, `Semantic Similarity`)
- [x] 실패 질의 사례 수집
- [x] 텍스트 실험 자동화 스크립트 구축 (`E1`, `E2`)
  - 산출물: `scripts/run_text_experiments.py`
- [x] 30문항 benchmark 결과 요약 리포트 작성
  - 산출물: `results/text_q30_experiment_report.md`, `results/text_experiment_summary_q30.csv`, `results/text_q30_metrics_summary.csv`
- [x] 실험 실행/비교 가이드 문서화
  - 산출물: `TEXT_EXPERIMENTS.md`
- [x] 산출물: `results/text_metrics.csv`, 실패 사례 노트
  - 산출물: `results/runs/<run_tag>/text_metrics.csv`, `results/runs/<run_tag>/text_failure_notes.md`, `results/runs/<run_tag>/text_structure_metrics.json`, `results/runs/<run_tag>/generation/text_generation_*.json` (9설정: `fixed_{64,128,256,512}`, `structure_text_{64,128,256,512}`, `token_256`)
  - 정답 채점 산출물: `results/runs/<run_tag>/text_answer_correctness_summary.csv`, `results/runs/<run_tag>/text_answer_correctness_detailed.csv`
  - 실행 스크립트: `scripts/run_text_full_pipeline.py`
  - 최신 완료 run: `results/runs/text_benchmark_20260315_en/`
  - 최신 완료 산출물:
    - `results/runs/text_benchmark_20260315_en/text_metrics.csv`
    - `results/runs/text_benchmark_20260315_en/text_answer_correctness_summary.csv`
    - `results/runs/text_benchmark_20260315_en/text_answer_correctness_detailed.csv`
    - `results/runs/text_benchmark_20260315_en/tables/text_metrics_summary.md`
    - `results/runs/text_benchmark_20260315_en/tables/text_metrics_full_summary.md`

### T4. 텍스트 분석/정리
- [x] baseline/proposed 차이 분석
- [x] chunk size 민감도 분석
- [x] 텍스트 실패 케이스 분류 (질의 유형/길이/경계 의존성)
- [x] 산출물: `results/runs/<run_tag>/tables/text_*`, `results/runs/<run_tag>/figures/text_*`, `results/runs/<run_tag>/analysis_notes.md`
  - 최신 완료 산출물:
    - `results/runs/text_benchmark_20260315_en/tables/text_baseline_vs_proposed.csv`
    - `results/runs/text_benchmark_20260315_en/tables/text_chunk_sensitivity.csv`
    - `results/runs/text_benchmark_20260315_en/tables/text_failure_cases_by_type.csv`
    - `results/runs/text_benchmark_20260315_en/analysis_notes.md`



## 코드 트랙

### C1. 데이터셋/질의셋
- [x] 코드 데이터셋 파일 단위 메타데이터 표준화
- [x] 평가용 질의셋 초안 작성
- [ ] 실제 코드 데이터셋 확장
- [ ] 질의셋 확장 (권장 30+)
- [x] 산출물: `data/text/eval/queries_code.jsonl`
  - 현재 상태: 5개 질의, placeholder 중심

### C2. 코드 구조 인식 청킹
- [x] Python `ast` 기반 class/function/control block 청킹
- [x] 부모 컨텍스트 메타데이터 주입
  - [x] 예: `Parent: Class X > def y`
- [x] orphan 코드 탐지 로직(초기 버전) 구현
- [x] 산출물: `data/processed/chunks_structure_code.json`

### C3. 코드 본실험
- [ ] 코드 질의셋으로 retrieval 평가
- [ ] 구조 지표 산출 (`Syntax Error Rate`, `Orphan Code Ratio`, `Executable Chunk Ratio`)
- [ ] 생성 지표 또는 코드 QA 품질 평가
- [ ] baseline/proposed 차이 로그 저장
- [ ] 산출물: `results/code_metrics.csv`
  - 현재 상태: 결과 파일 없음

### C4. 코드 분석/정리
- [ ] 부모 컨텍스트 보존 효과 분석
- [ ] 잘린 코드 조각이 검색 품질에 미치는 영향 분석
- [ ] 코드 실패 케이스 분류 (함수형 질의/예외 처리/호출 체인)
- [ ] 산출물: `results/tables/code_*`, `results/figures/code_*`, `docs/analysis_notes.md`

## 공통 확장 트랙

### X1. 재사용성 실험
- [ ] 동일 인덱스로 2개 이상 태스크 수행
  - [ ] 예: QA + 요약/문서화
- [ ] 태스크 전환 시 성능 유지/저하 기록
- [ ] 산출물: `results/reuse_metrics.md`

### X2. 어블레이션
- [ ] 메타데이터 제거/유지 비교
- [ ] RRF on/off 비교
- [ ] overlap/size 민감도 비교
- [ ] 산출물: `results/ablation.csv`

### X3. 결과 시각화
- [ ] 핵심 표 3개 작성 (텍스트/코드/재사용성)
- [ ] 핵심 그래프 2~4개 작성 (chunk size vs 성능 중심)
- [ ] figure 캡션 초안 작성
- [ ] 산출물: `results/figures/*`, `results/tables/*`

### X4. 해석 및 최종 패키징
- [ ] 왜 개선되는지 구조적 근거 정리
- [ ] 위협요인(데이터 편향, 질의셋 규모, 일반화 한계) 명시
- [ ] 재현 실행 순서 문서화 (`README` 또는 `RAG_PIPELINE.md` 갱신)
- [ ] 결과 요약 1페이지 작성
- [ ] 발표/논문용 핵심 기여 3~5줄 정제
- [ ] 산출물: `docs/analysis_notes.md`, 최종 요약본 + 재현 가이드

## 추가 활동 로그 (2026-03-12 반영)

### A. 텍스트 데이터/평가셋 정리
- [x] Harry Potter 텍스트 트랙 전용 경로(`data/text/raw`, `data/text/processed`, `data/text/eval`) 기준으로 데이터셋 구조 정리
- [x] 메인 질의셋, 30문항 벤치마크, 100문항 템플릿, qrels 파일 구성
- [x] 평가셋 설명 문서 작성

### B. 텍스트 실험 자동화/분석
- [x] `E1`(전략 비교) 자동 실행 스크립트 작성
- [x] `E2`(chunk size sweep) 자동 실행 스크립트 작성
- [x] 30문항 기준 결과 요약 리포트 작성 및 CSV 요약 저장
- [x] 라이브 재평가 결과 저장
  - 산출물: `results/text_fixed_metrics_live.json`, `results/text_fixed_metrics_live_q30.json`
- [x] 영어 EXAONE 생성 기반 9설정 benchmark run 완료
  - 산출물: `results/runs/text_benchmark_20260315_en/generation/text_generation_*.json`
- [x] 정답 기반 correctness 평가 완료
  - 산출물: `results/runs/text_benchmark_20260315_en/text_answer_correctness_summary.csv`, `results/runs/text_benchmark_20260315_en/text_answer_correctness_detailed.csv`
- [x] 발표용 요약표/전체표 생성 완료
  - 산출물: `results/runs/text_benchmark_20260315_en/tables/text_metrics_summary.md`, `results/runs/text_benchmark_20260315_en/tables/text_metrics_full_summary.md`

### C. 정답 라벨링 보조 작업
- [x] paragraph ID 기반 코퍼스 생성 스크립트 작성
- [x] BM25 기반 gold paragraph 후보 추천 스크립트 작성
- [x] 질의셋 라벨링 워크플로 문서화

### D. 운영/검증 보조 작업
- [x] 텍스트 데이터 audit 스크립트 작성
- [x] interactive 질의용 CLI 스크립트 작성
  - 산출물: `question.py`
- [x] interactive 답변 언어 선택(English/Korean) 추가
  - 산출물: `question.py`, `rag_pipeline/prompt.py`, `rag_pipeline/rag_chain.py`
- [x] TODO/실험 문서/파이프라인 문서 최신화
  - 관련 파일: `RESEARCH_2W_TODO.md`, `RAG_PIPELINE.md`, `README.md`, `TEXT_EXPERIMENTS.md`

### E. 파이프라인 동기화 수정
- [x] 텍스트 실험 경로와 평가 흐름에 맞춰 파이프라인 관련 파일 수정
  - 관련 파일: `config.py`, `main.py`, `scripts/build_index.py`, `scripts/chunk_dataset.py`, `scripts/chunk_papers.py`, `scripts/eval_detailed_report.py`, `scripts/eval_retrieval.py`, `scripts/search_with_metadata.py`

## 운영 규칙 (권장)
- 하루 시작: 당일 목표 3개만 고정
- 하루 종료: 지표/로그/실패 사례를 반드시 파일로 남김
- 실험 실행 시: 모든 run에 `run_tag` 또는 `timestamp`, `chunking_mode`, `chunk_size`, `overlap` 기록
- 텍스트 전체 실험은 `results/runs/<run_tag>/` 아래에 보존

## 즉시 실행 우선순위 (현재 기준)
1. [완료] 텍스트 트랙: 구조/생성 지표 추가 + 요약 결과를 `text_metrics.csv` 형태로 정리
2. [미착수] 코드 트랙: placeholder 질의셋/데이터셋을 실제 실험셋으로 교체
3. [미착수] 공통 확장: 구조 지표/생성 지표 계산 규칙 문서화

## 완료 로그 (2026-02-15)
- [완료] `scripts/chunk_dataset.py` 추가: `fixed|line|token|structure_text|structure_code` 통합 인터페이스 구축
- [완료] `scripts/chunk_papers.py`를 통합 스크립트와 호환 유지하도록 정리
- [완료] 모드별 청크 생성:
  - `data/processed/chunks_fixed.json`
  - `data/processed/chunks_structure_text.json`
- [완료] 모드별 인덱스/메타데이터 생성:
  - `vector_db/faiss_fixed.index`
  - `vector_db/faiss_structure_text.index`
  - `data/processed/chunks_fixed_metadata.json`
  - `data/processed/chunks_structure_text_metadata.json`
- [완료] 평가 스크립트 추가: `scripts/eval_retrieval.py` (`HitRate@K`, `MRR`)
- [완료] 1차 텍스트 비교 결과 저장:
  - `results/text_fixed_metrics.json`
  - `results/text_structure_text_metrics.json`
- [완료] 의존성 정리:
  - `rank-bm25` 설치 및 `requirements.txt` 반영
  - `langchain-community` 설치 및 `requirements.txt` 반영
- [완료] EXAONE 로드 안정화:
  - `rag_pipeline/rag_chain.py`에 모델 `revision`/`code_revision` 고정
- [완료] 실쿼리 E2E 검증:
  - `python3 main.py --query "Who is Dudley?" --k 3` 검색/생성 진입 확인

## 완료 로그 (2026-03-08)
- [완료] `scripts/chunk_dataset.py` 업데이트: 
  - Python AST 기반 구조 인식 청킹(`structure_code`) 구현
  - 부모 컨텍스트(`parent`) 추적 및 고아 코드(`is_orphan`) 탐지 로직 추가
- [완료] `rag_pipeline/retriever.py` 개선: 
  - FAISS(Dense)와 BM25(Sparse) 검색 결과를 결합하는 RRF(Reciprocal Rank Fusion) 알고리즘 설계 및 통합
- [완료] 하이브리드 검색 파이프라인 연동:
  - `scripts/search_with_metadata.py`에 BM25 인덱스 로드 및 RRF 검색 적용
  - `scripts/eval_retrieval.py` 평가 스크립트에 하이브리드 `retrieve` 인터페이스 적용 완료
- [완료] 구조적 메타데이터 직렬화(Serialization) 파이프라인 구축: 
  - `scripts/inject_metadata.py` 추가 (검색 엔진이 구조를 인식할 수 있도록 청크 텍스트 맨 앞에 메타데이터 헤더 결합)
  - Data Injection -> Re-indexing -> Evaluation으로 이어지는 3단계 파이프라인 확립
- [완료] 구조 인식 검색 E2E 스모크 테스트:
  - 텍스트/코드 도메인 하이브리드 검색 실행 및 로직 검증 완료
