# Retrieval Quality Evaluation Report
## Structure-Aware Chunking vs. Fixed-Size Chunking on Legacy Python Codebase

**Document Type:** Technical Evaluation Report  
**Stage:** Phase 1 — Retrieval Quality Assessment  
**Dataset:** requests v2.7.0 (Python HTTP Library)  
**Query Set:** 32 human-authored queries (English), stratified by difficulty  
**Evaluation Date:** 2026-03-27  

---

## 1. Overview

This report presents the retrieval quality evaluation results comparing two chunking strategies applied to a legacy Python codebase:

- **Structure-Aware Chunking (SAC):** AST-based segmentation that preserves function-level structural boundaries, with hierarchical parent metadata injection.
- **Fixed-Size Chunking (FSC):** Token-window-based segmentation using `RecursiveCharacterTextSplitter`, applied uniformly across chunk size conditions.

Both strategies were evaluated under four chunk size budgets (128, 256, 500, 1500 tokens) using a hybrid retrieval system combining BM25 and FAISS dense retrieval with Reciprocal Rank Fusion (RRF).

---

## 2. Evaluation Setup

| Component | Configuration |
| :--- | :--- |
| Codebase | psf/requests v2.7.0 |
| Files indexed | adapters.py, api.py, auth.py, cookies.py, hooks.py, models.py, sessions.py, utils.py |
| Query set | 32 queries (English), difficulty: easy / medium / hard |
| Retrieval system | BM25 + FAISS (cosine similarity), RRF fusion |
| Embedding model | sentence-transformers (384-dim) |
| Top-K | k = 5 |
| Relevance criterion | Symbol-level matching via AST parent metadata |

---

## 3. Metrics Definition

| Metric | Description |
| :--- | :--- |
| **Hit Rate@1** | Proportion of queries where the gold chunk ranks 1st |
| **Hit Rate@5** | Proportion of queries where the gold chunk appears in Top-5 |
| **MRR** | Mean Reciprocal Rank — rank-weighted retrieval accuracy |
| **nDCG@10** | Normalized Discounted Cumulative Gain at cutoff 10 |

A retrieved chunk is considered **relevant** if and only if the target symbol (class or function name) is present in the chunk's structural parent metadata. This strict criterion ensures fair comparison independent of chunk size effects on text overlap.

---

## 4. Results

### 4.1 Full Results Table

| Method | Chunk Size | Hit Rate@1 | Hit Rate@5 | MRR | nDCG@10 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **SAC** | 128 | 0.2500 | 0.4688 | 0.3354 | 0.3610 |
| **SAC** | 256 | 0.1875 | 0.4375 | 0.2745 | 0.3062 |
| **SAC** | 500 | 0.2188 | 0.4375 | 0.3073 | 0.3323 |
| **SAC** | 1500 | **0.2812** | **0.5312** | **0.3563** | **0.3893** |
| Fixed | 128 | 0.1250 | 0.1562 | 0.1313 | 0.1371 |
| Fixed | 256 | 0.0938 | 0.1875 | 0.1260 | 0.1374 |
| Fixed | 500 | 0.0938 | 0.1875 | 0.1354 | 0.1483 |
| Fixed | 1500 | 0.1875 | 0.2500 | 0.2188 | 0.2209 |

### 4.2 Hit Rate@5 by Chunk Size

| Chunk Size | Fixed Hit@5 | SAC Hit@5 | Improvement |
| :---: | :---: | :---: | :---: |
| 128 | 0.1562 | 0.4688 | **+200.1%** |
| 256 | 0.1875 | 0.4375 | **+133.3%** |
| 500 | 0.1875 | 0.4375 | **+133.3%** |
| 1500 | 0.2500 | 0.5312 | **+112.5%** |

### 4.3 MRR by Chunk Size

| Chunk Size | Fixed MRR | SAC MRR | Improvement |
| :---: | :---: | :---: | :---: |
| 128 | 0.1313 | 0.3354 | **+155.5%** |
| 256 | 0.1260 | 0.2745 | **+117.9%** |
| 500 | 0.1354 | 0.3073 | **+127.0%** |
| 1500 | 0.2188 | 0.3563 | **+62.9%** |

---

## 5. Analysis

### 5.1 SAC Consistently Outperforms FSC Across All Conditions

SAC achieves superior retrieval performance across all four chunk size budgets and all four metrics without exception. At chunk_size=1500, SAC achieves a Hit Rate@5 of 0.5312 compared to FSC's 0.2500, a 2.1× improvement. At chunk_size=128, the gap widens further, with SAC reaching 0.4688 while FSC falls to 0.1562, a 3× improvement.

### 5.2 FSC Degrades Rapidly Under Reduced Chunk Size

FSC exhibits severe performance degradation as chunk size decreases. Hit Rate@5 drops from 0.2500 at size 1500 to 0.1562 at size 128, a 37.5% relative decline. MRR drops from 0.2188 to 0.1313, a 40.0% decline. This pattern confirms that FSC's structural fragmentation becomes increasingly destructive as the token budget shrinks.

### 5.3 SAC Maintains Robust Performance Under Reduced Chunk Size

In contrast, SAC demonstrates substantially greater robustness. Hit Rate@5 ranges from 0.4375 to 0.5312 across all chunk size conditions, a maximum variance of 0.0937. MRR ranges from 0.2745 to 0.3563, remaining stable relative to FSC's collapse. This robustness is attributable to SAC's alignment of chunk boundaries with AST-defined structural units, which preserves symbol-level completeness regardless of the token budget.

### 5.4 SAC Achieves Best Performance at Largest Chunk Size

SAC peaks at chunk_size=1500 across all metrics, which is consistent with the design principle that larger function-level chunks contain more complete structural context. FSC also peaks at 1500, but at substantially lower absolute values, indicating that the performance gap is driven by structural alignment rather than chunk size alone.

---

## 6. Key Findings

**Finding 1.** SAC outperforms FSC by a factor of 2.1× to 3.0× in Hit Rate@5 depending on chunk size, demonstrating that structural boundary preservation is the primary driver of retrieval quality improvement.

**Finding 2.** FSC degrades by 37.5% in Hit Rate@5 as chunk size decreases from 1500 to 128. SAC degrades by only 11.7% over the same range, confirming that structure-aware segmentation provides robustness under constrained chunk size budgets.

**Finding 3.** The performance gap between SAC and FSC is largest at the smallest chunk size (128 tokens), precisely the condition where structural fragmentation under FSC is most destructive. This directly validates the core research hypothesis that chunking failure is a structural design problem, not a hyperparameter tuning problem.

---

## 7. Limitations

The following limitations should be noted when interpreting these results.

**Query set size.** The evaluation is conducted on 32 queries, which provides directional evidence but may not reach statistical significance thresholds for all sub-group comparisons. A larger query set with inter-annotator agreement measurement is recommended for full-paper submission.

**Relevance criterion strictness.** The symbol-level matching criterion may underestimate absolute retrieval performance for chunks that contain partial but useful information. Absolute Hit Rate values should be interpreted relative to this criterion rather than as absolute performance bounds.

**Single codebase.** Results are derived from a single open-source library (requests v2.7.0). Generalizability to other codebases with different structural characteristics has not been verified in this evaluation phase.

**Embedding model.** A general-purpose sentence-transformer (384-dim) was used. Code-specific embedding models such as CodeBERT or UniXcoder may yield higher absolute performance for both strategies.

---

## 8. Conclusion

Structure-Aware Chunking (SAC) consistently and substantially outperforms Fixed-Size Chunking (FSC) across all chunk size conditions evaluated. The results confirm that chunking boundary alignment with AST-defined structural units is essential for reliable code retrieval, and that this alignment provides robustness under aggressive chunk size reduction. These findings support the central claim of this research: that chunking is a structural design decision, not a hyperparameter tuning problem.

---

*This document covers Phase 1 evaluation only. Generation quality results (RAGAS Faithfulness, Answer Relevance) are reported separately in the Phase 2 document.*
