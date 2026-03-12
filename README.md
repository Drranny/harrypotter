# Structure-Aware Hybrid RAG

본 프로젝트는 `route.pdf` 연구 방향을 기반으로, RAG 청킹을 단순 전처리가 아닌 **구조 설계 문제**로 다룹니다.

핵심 목표는 다음 두 도메인에서 구조 인식 청킹의 효과를 검증하는 것입니다.
- 텍스트 도메인: Harry Potter 데이터
- 코드 도메인: Legacy Python 코드(추후 추가 가능)

## 연구 문제
- 기존 fixed/line/token 청킹은 의미 단위와 구조 단위를 자주 분리한다.
- 이로 인해 검색 시 문맥 단절, precision 저하, 코드에서는 실행 불가능 조각(orphan) 문제가 발생한다.
- 따라서 chunk size 튜닝 이전에, **구조 보존형 청킹**이 필요하다.

## 제안 접근
- Text: 문단/챕터 경계 기반 `structure_text` 청킹
- Code: AST 기반 `structure_code` 청킹 (`class`/`def`/제어 블록 단위)
- Retrieval: FAISS(semantic) + BM25(keyword) + RRF fusion
- Generation: Strict Grounding 기반 응답

## 시스템 개념 아키텍처
1. Raw Data(Text/Code)
2. Structure-Aware Chunking
3. Embedding + Indexing
4. Hybrid Retrieval(BM25 + FAISS)
5. RRF Re-ranking
6. LLM Generation

## 기대 기여
- Chunking을 Information Reuse 관점의 핵심 설계 요소로 정리
- 텍스트/코드 도메인 공통으로 적용 가능한 구조 기반 전처리 전략 제시
- 코드 QA, 레거시 분석, 문서화 자동화로의 실무 확장 가능성 확보

## 문서 안내
- 실행/운영/협업 규칙: `RAG_PIPELINE.md`
- 2주 작업 계획: `RESEARCH_2W_TODO.md`
- 박람회 전달 가이드: `HANDOFF_EXPO.md`
- 팟 분리 온보딩 가이드: `POD_SPLIT_ONBOARDING.md`
- 과목용(웹 연동) 온보딩 가이드: `COURSE_ONBOARDING.md`
- 텍스트 전용 실험 가이드: `TEXT_EXPERIMENTS.md`
