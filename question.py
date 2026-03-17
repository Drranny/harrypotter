#!/usr/bin/env python3
import json
import os
from rank_bm25 import BM25Okapi
import faiss
from ingest.embed import model
from rag_pipeline.retriever import retrieve as hybrid_retrieve
from rag_pipeline.prompt import build_prompt
from rag_pipeline.rag_chain import rag_answer

# Step 1: Choose retrieval method
print("\n=== Which method do you want to use? ===")
print("1) faiss   (semantic search)")
print("2) bm25    (keyword search)")
print("3) hybrid  (semantic + keyword, recommended)")
method = input("\nSelect (1/2/3) [default: 3]: ").strip() or "3"

method_map = {"1": "faiss", "2": "bm25", "3": "hybrid"}
retriever = method_map.get(method, "hybrid")

# Step 2: Choose answer language
print("\n=== Which answer language do you want? ===")
print("1) English")
print("2) Korean")
language_choice = input("\nSelect (1/2) [default: 1]: ").strip() or "1"
language_map = {"1": "English", "2": "Korean"}
answer_language = language_map.get(language_choice, "English")

# Step 3: Choose chunk mode and size
print("\n=== Which chunk mode/size? ===")
configs = []
for mode in ["fixed", "token", "structure_text"]:
    for size in [64, 128, 256, 512]:
        path = f"data/text/processed/chunks_{mode}_{size}_metadata.json"
        if os.path.exists(path):
            configs.append((f"{mode}_{size}", mode, size))

for i, (name, _, _) in enumerate(configs, 1):
    print(f"{i}) {name}")

default_idx = next((i for i, (n, _, _) in enumerate(configs, 1) if n == 'structure_text_512'), 1)
config_idx = input(f"\nSelect (1-{len(configs)}) [default: {default_idx}]: ").strip()
config_idx = int(config_idx) - 1 if config_idx else default_idx - 1
chosen_mode, chosen_size = configs[config_idx][1], configs[config_idx][2]

print(f"\n→ Using: {retriever} + {chosen_mode}_{chosen_size}")
print(f"→ Answer language: {answer_language}")

# Step 4: Ask question
print("\n=== Write your question ===")
question = input("> ").strip()

if not question:
    print("No question provided.")
    exit(1)

# Load chunks
chunks_path = f"data/text/processed/chunks_{chosen_mode}_{chosen_size}_metadata.json"
with open(chunks_path, 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# Build retrieval indices
if retriever in {"faiss", "hybrid"}:
    index_path = f"vector_db/faiss_text_{chosen_mode}_{chosen_size}.index"
    index = faiss.read_index(index_path)

if retriever in {"bm25", "hybrid"}:
    tokenized = [chunk.get("text", "").split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized)

# Retrieve
top_k = 5
if retriever == "hybrid":
    docs = hybrid_retrieve(question, index, chunks, k=top_k, bm25=bm25)
elif retriever == "faiss":
    q_vec = model.encode([question])
    ids = index.search(q_vec, min(top_k * 10, len(chunks)))[1][0]
    docs = [chunks[i] for i in ids if i >= 0][:top_k]
else:  # bm25
    scores = bm25.get_scores(question.split())
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    docs = [chunks[i] for i in ranked[:top_k]]

# Print results
print("\n" + "="*80)
print(f"📌 Query: {question}")
print(f"📊 Method: {retriever} | Chunks: {chosen_mode}_{chosen_size}")
print("="*80)
for i, doc in enumerate(docs, 1):
    src = doc.get('source_file', '?')
    text = doc.get('text', '').replace('\n', ' ')[:150]
    print(f"\n[{i}] {src}")
    print(f"    {text}...")
print("\n" + "="*80)

# Generate answer using EXAONE LLM
print("\n\n🤖 Generating answer from LG AI EXAONE...\n")
contexts = [doc.get('text', '') for doc in docs]
prompt = build_prompt(contexts, question, answer_language=answer_language)
answer = rag_answer(prompt, answer_language=answer_language)

print("\n" + "="*80)
print("✨ FINAL ANSWER")
print("="*80)
print(answer)
print("="*80)
