#!/usr/bin/env python3
"""
MemOS Research Benchmark Suite
Runs the real-database empirical benchmark engine and outputs mathematical metrics.
Requires PostgreSQL + Qdrant + Neo4j + Redis + Ollama running (see docs/BENCHMARKING.md).
"""

from real_benchmark import run_benchmark

if __name__ == "__main__":
    run_benchmark()
