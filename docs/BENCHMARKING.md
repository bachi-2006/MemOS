# MemOS — Empirical Research Benchmarking & Evaluation Methodology

> **Target Scope:** Comparative evaluation of Raw Local LLM vs. Naive Vector RAG vs. MemOS Multi-Store Framework.

---

## 🎯 Evaluation Objectives & Baselines

To rigorously evaluate recall, precision, ranking accuracy, lifecycle efficiency, and latency trade-offs:
1. **Baseline A — Raw LLM**: Local LLM execution with zero long-term memory or external context augmentation.
2. **Baseline B — Naive Vector RAG**: Standard single-vector cosine similarity top-$k$ retrieval over unstructured chunks.
3. **Proposed System — MemOS Multi-Store Framework**: Hybrid Vector Indexing (Qdrant) + Knowledge Graph Associative Links (Neo4j) + Auto-Learned User Profile (PostgreSQL) + Dynamic Importance Lifecycle Filtering.

---

## 📐 Mathematical Metric Definitions

1. **Precision@K**:
   $$\text{Precision@K} = \frac{|\text{Relevant Ground Truth} \cap \text{Retrieved@K}|}{K}$$

2. **Recall@K**:
   $$\text{Recall@K} = \frac{|\text{Relevant Ground Truth} \cap \text{Retrieved@K}|}{|\text{Relevant Ground Truth}|}$$

3. **Mean Reciprocal Rank (MRR)**:
   $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

4. **Dynamic Importance Decay Formula**:
   $$\text{Importance} = (\text{Recency} \times 0.3) + (\text{Frequency} \times 0.3) + (\text{EntityRichness} \times 0.2) + (\text{Confidence} \times 0.2) + \text{PinBonus}$$

5. **Token Compression Ratio**:
   $$\text{Compression Ratio} = \frac{\text{Uncompressed Tokens} - \text{Compressed Tokens}}{\text{Uncompressed Tokens}} \times 100\%$$

---

## ⚙️ How to Reproduce Benchmarks Locally

Run the empirical evaluation harness from the repository root:

```powershell
python scripts/real_benchmark.py
```

The script will automatically execute all test scenarios, compute mathematical ranking and lifecycle scores, print the benchmark table to stdout, and export raw results to `docs/BENCHMARK_RESULTS.json`.
