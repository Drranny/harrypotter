# Generation Quality Evaluation Report
## Structure-Aware Chunking vs. Fixed-Size Chunking on Legacy Python Codebase

**Document Type:** Technical Evaluation Report  
**Stage:** Phase 3 — Generation Quality Assessment  
**Dataset:** requests v2.7.0 (Python HTTP Library)  
**Query Set:** 32 human-authored queries (English), stratified by difficulty  
**Evaluation Date:** 2026-03-31  
**Version:** 1.0

---

## 1. Overview

This report presents the generation quality evaluation results comparing two chunking strategies across four chunk size conditions using a Retrieval-Augmented Generation (RAG) pipeline applied to a legacy Python codebase.

- **Structure-Aware Chunking (SAC):** AST-based segmentation preserving function-level structural boundaries with hierarchical parent metadata.
- **Fixed-Size Chunking (FSC):** Token-window-based segmentation using `RecursiveCharacterTextSplitter`.

Generation quality is evaluated using two RAGAS-inspired metrics: Answer Relevance and Faithfulness. This phase builds on Phase 1 (retrieval quality) and Phase 2 (structural integrity), and is designed to assess whether chunking strategy differences in retrieval precision propagate to downstream generation quality.

---

## 2. Evaluation Setup

| Component | Configuration |
| :--- | :--- |
| Codebase | psf/requests v2.7.0 |
| Query set | 32 queries (English) |
| Retrieval system | BM25 + FAISS (Jina embeddings, 768-dim), RRF fusion |
| Embedding model | jinaai/jina-embeddings-v2-base-code |
| LLM | OpenAI GPT-4o-mini (API) |
| Top-K | k = 5 |
| Prompt policy | Context-first with partial-evidence tolerance |
| Support threshold (Faithfulness) | 0.35 cosine similarity |

**Prompt policy note.** The generation prompt instructs the LLM to use retrieved code context as the primary reference and to construct answers from available evidence even when context is partial. The LLM is instructed to respond with "The provided documents do not contain the answer" only when the retrieved context has absolutely no relevance to the question. This policy was adopted after preliminary experiments with a strict "no outside knowledge" prompt yielded near-zero scores due to LLM refusal to answer when context was incomplete.

---

## 3. Metrics Definition

| Metric | Description |
| :--- | :--- |
| **Answer Relevance** | Cosine similarity between the query embedding and the answer embedding. Measures how directly the answer addresses the question. |
| **Faithfulness** | Fraction of answer sentences that are semantically supported by at least one retrieved context chunk (cosine similarity ≥ 0.35). Measures consistency between the answer and retrieved context. |

---

## 4. Results

### 4.1 Full Results Table

| Method | Chunk Size | Answer Relevance | Faithfulness |
| :--- | :---: | :---: | :---: |
| **SAC** | 128 | 0.4870 | 0.5755 |
| **SAC** | 256 | 0.4755 | 0.5462 |
| **SAC** | 500 | **0.6453** | **0.7389** |
| **SAC** | 1500 | 0.5984 | 0.6745 |
| Fixed | 128 | 0.4348 | 0.5938 |
| Fixed | 256 | 0.5063 | 0.6102 |
| Fixed | 500 | **0.6816** | **0.8174** |
| Fixed | 1500 | 0.6119 | 0.6732 |

### 4.2 SAC vs. FSC: Answer Relevance by Chunk Size

| Chunk Size | SAC | Fixed | Difference |
| :---: | :---: | :---: | :---: |
| 128 | **0.4870** | 0.4348 | SAC +0.0522 |
| 256 | 0.4755 | **0.5063** | Fixed +0.0308 |
| 500 | 0.6453 | **0.6816** | Fixed +0.0363 |
| 1500 | 0.5984 | **0.6119** | Fixed +0.0135 |

### 4.3 SAC vs. FSC: Faithfulness by Chunk Size

| Chunk Size | SAC | Fixed | Difference |
| :---: | :---: | :---: | :---: |
| 128 | 0.5755 | **0.5938** | Fixed +0.0183 |
| 256 | 0.5462 | **0.6102** | Fixed +0.0640 |
| 500 | 0.7389 | **0.8174** | Fixed +0.0785 |
| 1500 | **0.6745** | 0.6732 | SAC +0.0013 |

---

## 5. Analysis

### 5.1 Both Strategies Achieve Meaningful Generation Quality

All eight conditions produce substantive answers with Answer Relevance above 0.43 and Faithfulness above 0.54. This confirms that the GPT-4o-mini API backend is capable of utilizing retrieved code context effectively, and that the evaluation framework is functioning as intended.

### 5.2 chunk_size=500 Is the Optimal Configuration for Both Strategies

Both SAC and FSC peak at chunk_size=500 across both metrics. SAC_500 achieves Answer Relevance of 0.6453 and Faithfulness of 0.7389, while Fixed_500 achieves 0.6816 and 0.8174 respectively. This convergence at the same chunk size suggests that a token budget of approximately 500 tokens provides sufficient contextual content for LLM generation across both chunking strategies.

At chunk_size=128 and 256, both strategies show reduced performance, indicating that chunks too small to contain complete functional context limit LLM generation quality regardless of chunking method. At chunk_size=1500, performance also declines slightly from the 500-token peak for both strategies.

### 5.3 FSC Outperforms SAC on Faithfulness at Most Chunk Sizes

FSC achieves higher Faithfulness scores than SAC at chunk sizes 128, 256, and 500, with the largest gap at chunk_size=500 (+0.0785). At chunk_size=1500, the two strategies are nearly equivalent (Fixed 0.6732 vs. SAC 0.6745).

This result appears to contradict Phase 1 findings, where SAC achieved 2–3× higher Hit Rate@5 than FSC. The explanation lies in the distinction between what retrieval and generation metrics measure. RAGAS Faithfulness measures whether LLM answer sentences are semantically consistent with retrieved context chunks — not whether the retrieved chunks contain the ground-truth answer. FSC's larger chunks, even when retrieved via lower-precision retrieval, provide denser contextual content per chunk. This allows the LLM to generate plausible answers that are well-supported by the retrieved text, yielding higher Faithfulness scores even when the retrieved chunks are not the precise ground-truth units.

In contrast, SAC retrieves structurally precise chunks — often function-level units — which are shorter and contain more focused but narrower content. When retrieval succeeds, SAC provides more accurate contextual grounding. When retrieval partially fails, SAC's smaller chunks offer less fallback content for the LLM to draw upon, resulting in lower Faithfulness.

### 5.4 Answer Relevance Difference Between SAC and FSC Is Small

The Answer Relevance gap between SAC and FSC ranges from −0.0363 to +0.0522 depending on chunk size. At chunk_size=128, SAC leads by 0.0522. At chunk_sizes 256, 500, and 1500, FSC leads by 0.01–0.04. These differences are small in absolute terms and may not be statistically significant given the 32-query evaluation set.

### 5.5 Generation Quality Does Not Directly Reflect Retrieval Precision

A central observation from this phase is that generation quality metrics do not directly reflect Phase 1 retrieval precision differences. SAC's 2–3× advantage in Hit Rate@5 does not translate into a proportional advantage in generation quality. This finding highlights a fundamental measurement gap: retrieval precision (whether the correct structural unit is retrieved) and generation faithfulness (whether the answer is consistent with whatever was retrieved) are distinct properties that respond differently to chunking design choices.

This gap is not a failure of either strategy but a structural property of how RAGAS metrics interact with chunk granularity. It suggests that optimizing chunking for retrieval precision and optimizing for generation quality may require different design objectives.

---

## 6. Key Findings

**Finding 1.** Both SAC and FSC produce substantive generation quality with GPT-4o-mini, with Faithfulness ranging from 0.55 to 0.82 across all conditions.

**Finding 2.** chunk_size=500 is the optimal configuration for both strategies on Answer Relevance and Faithfulness, suggesting that this token budget best balances structural completeness with contextual density for LLM generation.

**Finding 3.** FSC achieves higher Faithfulness than SAC at chunk sizes 128, 256, and 500, with the largest gap at chunk_size=500 (+0.0785). This advantage is attributable to FSC's larger per-chunk contextual density rather than superior retrieval precision.

**Finding 4.** SAC's 2–3× retrieval precision advantage (Phase 1) does not translate into a proportional generation quality advantage, revealing a fundamental trade-off: fine-grained structural chunking improves retrieval precision but reduces per-chunk contextual density available for LLM generation.

**Finding 5.** At chunk_size=1500, SAC and FSC achieve nearly identical Faithfulness (0.6745 vs. 0.6732), suggesting that at large chunk sizes the structural alignment advantage of SAC and the density advantage of FSC converge.

---

## 7. Limitations

**Metric sensitivity to chunk size.** RAGAS Faithfulness is sensitive to the amount of context available per retrieved chunk. This introduces a systematic bias in favor of larger chunks regardless of retrieval precision, making it difficult to isolate the effect of chunking strategy from chunk size effects.

**Prompt policy dependency.** Generation quality is strongly influenced by the prompt policy. The partial-evidence tolerance prompt used here allows the LLM to generate answers from incomplete context, which increases Faithfulness scores for FSC relative to a strict grounding policy.

**Query set size.** The evaluation is conducted on 32 queries. Small performance differences may not be statistically significant at this sample size.

**Single LLM.** Results are based on GPT-4o-mini only. Different LLMs with different context utilization capabilities may yield different relative performance between SAC and FSC.

**No ground-truth answer evaluation.** This evaluation uses embedding-based proxy metrics rather than human-evaluated answer correctness. Ground-truth answer comparison would provide stronger evidence of generation quality differences.

---

## 8. Conclusion

Generation quality evaluation reveals a trade-off not apparent from retrieval metrics alone. While SAC achieves substantially higher retrieval precision than FSC (Phase 1), this advantage does not translate into uniformly higher generation quality. FSC's larger chunks provide denser contextual content per retrieved unit, which benefits LLM generation under the RAGAS Faithfulness metric. At chunk_size=1500, the two strategies converge to nearly identical Faithfulness scores.

These findings suggest that chunking strategy design involves competing objectives: structural precision for retrieval versus contextual density for generation. SAC optimizes for the former, FSC for the latter. Future work should explore hybrid approaches — such as SAC-based retrieval with context expansion at generation time — that preserve structural retrieval precision while providing sufficient contextual density for LLM generation.

---

*This document covers Phase 3 generation quality evaluation. Retrieval quality results (Hit Rate, MRR, nDCG) are reported in the Phase 1 document. Structural integrity results (Syntax Error Rate, Orphan Code Ratio) are reported in the Phase 2 document.*
