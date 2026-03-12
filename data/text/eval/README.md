# Text Eval Dataset (Harry Potter)

## Files
- `queries_text_main.jsonl`: 현재 실행용 질의셋(소규모, 빠른 검증)
- `queries_text_benchmark30.jsonl`: 논문 실험 샘플 벤치마크(30문항)
- `queries_text_benchmark30.csv`: 벤치마크 CSV 포맷
- `queries_text_100_template.jsonl`: 논문 실험용 100문항 템플릿(Type A/B/C)
- `qrels_text_main.csv`: `queries_text_main.jsonl`용 정답 source 매핑

## JSONL schema
각 줄은 아래 형태를 따릅니다.

```json
{
  "qid": "text_001",
  "query": "Who is Harry's godfather?",
  "query_type": "A|B|C",
  "gold_sources": ["Book3.txt"],
  "gold_paragraph_ids": ["book_3_chapter_19_paragraph_4"]
}
```

## Query type meaning
- `A`: factual retrieval (짧은 fact)
- `B`: paragraph explanation (단락 설명)
- `C`: multi-context reasoning (다중 문맥 추론)

## Notes

## Split policy
- retrieval corpus: `data/text/raw/*`
- dev set: `queries_text_main.jsonl`
- fixed benchmark test set: `queries_text_benchmark30.jsonl`
- expansion pool: `queries_text_100_template.jsonl`
- `queries_text_100_template.jsonl`은 gold label 확정 전 공식 성능 비교에 사용하지 않음
