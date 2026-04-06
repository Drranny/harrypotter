#!/bin/bash
cd /home/selee/SAC-project
source .venv/bin/activate
export OPENAI_API_KEY="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"

for mode in structure fixed; do
  for size in 128 256 500 1500; do
    outfile="results/code_generation_${mode}_${size}_jina.json"
    if [ -f "$outfile" ]; then
      echo "[SKIP] $outfile already exists"
      continue
    fi
    echo "[RUN] $mode $size"
    python scripts/eval_code_generation.py \
      --queries data/eval/queries_code.jsonl \
      --chunks "data/processed/code_${mode}_${size}_jina_metadata.json" \
      --index "vector_db/faiss_code_${mode}_${size}_jina.index" \
      --k 5 \
      --answer-mode llm \
      --out "$outfile"
  done
done
echo "[ALL DONE]"
