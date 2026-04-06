# Structure-Aware Chunking for Code RAG: Empirical Evidence from a Legacy Python Codebase

**Authors:** [Author Names] | **Affiliation:** [Institution]

---

## Abstract

We present a systematic empirical comparison of Structure-Aware Chunking (SAC), which segments code along Abstract Syntax Tree (AST) boundaries with hierarchical metadata injection, against Fixed-Size Chunking (FSC) for code Retrieval-Augmented Generation (RAG). Experiments are conducted on psf/requests v2.7.0 across four chunk sizes (128–1500 tokens), two embedding models, and three evaluation phases: retrieval quality, structural integrity, and generation quality. SAC outperforms FSC by 2.0–3.2× in Hit Rate@5 and reduces Syntax Error Rate by up to 63.19 percentage points. A mechanism decomposition analysis shows that SAC's retrieval advantage operates through two independent layers: structural metadata preservation (active at all chunk sizes) and AST boundary-level segmentation (active at chunk_size ≥ 500). We further identify a fundamental trade-off between structural precision for retrieval and contextual density for generation.

**Keywords:** Retrieval-Augmented Generation, Code Chunking, Abstract Syntax Tree, Information Retrieval

---

## 1. Introduction

Chunking — dividing source code into retrievable units — is a critical yet underexplored design variable in code RAG pipelines. Most deployed systems apply fixed-size splitting that treats code as undifferentiated text, fragmenting function bodies and class definitions at arbitrary token boundaries. Recent work (Xie et al., 2025) demonstrates that AST-based chunking improves retrieval recall, but the mechanisms underlying this improvement remain unclear.

This paper makes four contributions: (1) a three-phase evaluation framework covering retrieval quality, structural integrity, and generation quality; (2) a mechanism decomposition analysis separating SAC's advantage into metadata preservation and boundary-level segmentation; (3) empirical evidence that metadata injection alone provides 2–3× retrieval improvement; and (4) identification of a retrieval-generation trade-off with implications for RAG pipeline design.

---

## 2. Methodology

**Dataset.** psf/requests v2.7.0 (8 Python source files). Query set: 32 human-authored English queries annotated with gold symbols (target class/function names).

**Chunking.** SAC traverses the Python AST to extract function-level chunks with hierarchical parent metadata (`class:X > function:Y`). When AST nodes exceed the chunk budget, fixed-size fallback is applied within the node, preserving metadata. FSC applies `RecursiveCharacterTextSplitter` uniformly with no metadata. Both strategies are evaluated at chunk sizes 128, 256, 500, and 1500 tokens.

**Retrieval.** Hybrid BM25 + FAISS with Reciprocal Rank Fusion (RRF, k=60). Two embedding models: MiniLM (384-dim, general-purpose) and Jina (768-dim, code-specialized). Top-5 retrieval (k=5).

**Evaluation.** Phase 1: Hit Rate@1/5, MRR, nDCG@10 with symbol-level strict matching. Phase 2: Syntax Error Rate (SER) and Orphan Code Ratio (OCR). Phase 3: Answer Relevance and Faithfulness (RAGAS-inspired) using GPT-4o-mini.

---

## 3. SAC Mechanism Analysis

SAC applies fixed-size fallback when AST nodes exceed the chunk budget. Table 1 shows that at small chunk sizes, the vast majority of SAC chunks are produced via fallback — yet all retain structural parent metadata.

**Table 1: SAC Fallback Distribution**

| Chunk Size | Total Chunks | Fallback Rate |
|:---:|:---:|:---:|
| 128 | 1,369 | 97.8% |
| 256 | 716 | 90.9% |
| 500 | 389 | 69.9% |
| 1500 | 216 | 16.7% |

This reveals two independent advantage mechanisms: **Layer 1 (metadata)** — active at all chunk sizes, as fallback chunks retain `class:X > function:Y` metadata that FSC entirely lacks; **Layer 2 (boundary)** — active at chunk_size ≥ 500, where 30–83% of chunks are genuine AST-boundary units providing complete function-level context.

---

## 4. Results

### 4.1 Phase 1: Retrieval Quality

**Table 2: Retrieval Quality (Hit Rate@5, MRR, Jina embedding)**

| Method | Size | Hit@5 | MRR | nDCG@10 | Mechanism |
|:---|:---:|:---:|:---:|:---:|:---:|
| SAC | 128 | 0.5625 | 0.3578 | 0.4085 | Metadata |
| SAC | 256 | 0.5000 | 0.3568 | 0.3876 | Metadata |
| **SAC** | **500** | **0.6875** | **0.4068** | **0.4817** | Metadata + Boundary |
| SAC | 1500 | 0.6562 | 0.3786 | 0.4516 | Metadata + Boundary |
| Fixed | 128 | 0.1875 | 0.1276 | 0.1426 | — |
| Fixed | 256 | 0.1562 | 0.1198 | 0.1272 | — |
| Fixed | 500 | 0.2500 | 0.1745 | 0.1917 | — |
| Fixed | 1500 | 0.2812 | 0.2370 | 0.2418 | — |

SAC outperforms FSC by 2.0–3.2× in Hit Rate@5 across all conditions. At chunk_size=128 and 256, where fallback rates exceed 90% and segmentation is nearly identical to FSC, SAC still achieves 3× higher Hit Rate@5. This demonstrates that **metadata injection alone** is a primary driver of retrieval quality. The Jina model disproportionately benefits SAC (+0.2500 Hit@5 at chunk_size=500 vs. +0.0625 for FSC), confirming that code-specialized embeddings amplify structural advantages.

Under a relaxed file-level criterion, both strategies converge at Hit Rate@5 = 0.9688, validating the strict symbol-level criterion as necessary to differentiate chunking quality.

### 4.2 Phase 2: Structural Integrity

**Table 3: Structural Integrity (Syntax Error Rate)**

| Method | Size | SER (%) | OCR (%) |
|:---|:---:|:---:|:---:|
| **SAC** | **1500** | **9.26%** | 5.09% |
| Fixed | 1500 | 72.45% | 0.00% |
| **SAC** | **500** | **41.13%** | 5.66% |
| Fixed | 500 | 64.13% | 0.00% |
| **SAC** | **128** | **61.43%** | 5.26% |
| Fixed | 128 | 63.56% | 0.00% |

SAC reduces SER by 63.19 percentage points at chunk_size=1500, where 83.3% of chunks are genuine AST-boundary units. The advantage narrows at smaller chunk sizes due to fallback splitting, converging to near-parity at chunk_size=128. FSC's 0.00% OCR is a detection artifact from the indentation heuristic, not a true absence of orphan code.

### 4.3 Phase 3: Generation Quality

**Table 4: Generation Quality (GPT-4o-mini, Jina retrieval)**

| Method | Size | Answer Relevance | Faithfulness |
|:---|:---:|:---:|:---:|
| SAC | 128 | 0.4870 | 0.5755 |
| SAC | 256 | 0.4755 | 0.5462 |
| **SAC** | **500** | **0.6453** | **0.7389** |
| SAC | 1500 | 0.5984 | 0.6745 |
| Fixed | 128 | 0.4348 | 0.5938 |
| Fixed | 256 | 0.5063 | 0.6102 |
| **Fixed** | **500** | **0.6816** | **0.8174** |
| Fixed | 1500 | 0.6119 | **0.6732** |

Both strategies peak at chunk_size=500. FSC outperforms SAC on Faithfulness at chunk sizes 128, 256, and 500 (largest gap: +0.0785 at size 500), converging at chunk_size=1500 (SAC: 0.6745, Fixed: 0.6732). FSC's larger chunks provide denser contextual content per retrieved unit, enabling the LLM to generate plausible, context-consistent answers even without precise ground-truth retrieval. SAC's structurally precise but narrower chunks offer less fallback content when retrieval partially fails.

---

## 5. Discussion

**The dual role of metadata.** The mechanism decomposition analysis establishes that metadata injection — independent of boundary-level segmentation — provides substantial and consistent retrieval gains. This has a direct practical implication: systems constrained to fixed-size chunking can achieve substantial retrieval improvement by injecting structural provenance metadata derived from static analysis.

**The retrieval-generation trade-off.** SAC's 2–3× retrieval precision advantage does not translate into uniform generation quality improvement. RAGAS Faithfulness rewards contextual density over structural precision, creating a systematic bias toward larger chunks. This trade-off suggests that optimizing chunking for retrieval and generation may require different design objectives. A hybrid approach — SAC-based retrieval with context expansion at generation time — could preserve retrieval precision while providing sufficient contextual density for generation.

---

## 6. Conclusion

Structure-Aware Chunking consistently outperforms Fixed-Size Chunking across retrieval quality and structural integrity. The key finding is that SAC's advantage is layered: metadata preservation provides the baseline improvement at all chunk sizes, while AST boundary alignment provides a compounding advantage at larger chunk sizes. Generation quality reveals a complementary trade-off, with FSC's contextual density benefiting LLM faithfulness at most conditions. These findings support treating chunking as a structural design decision with two independent levers — metadata and boundary alignment — rather than a hyperparameter tuning problem.
