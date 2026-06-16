# app/retrieval_evaluation/evaluator.py

import json
from app.retrieval_evaluation.metrics import (
    top1_accuracy,
    top3_accuracy,
    precision_at_k,
    mean_reciprocal_rank
)


class RetrievalEvaluator:

    def __init__(self, retriever, conn):
        self.retriever = retriever
        self.conn = conn

    # ─────────────────────────────────────────────────────────

    def evaluate_query(self, sample):
        query = sample["query"]

        results = self.retriever.retrieve(self.conn, query)

        return {
            "query": query,
            "type": sample.get("type"),

            "top1": top1_accuracy(results, sample),
            "top3": top3_accuracy(results, sample),
            "p_at_5": precision_at_k(results, sample, k=5),
            "mrr": mean_reciprocal_rank(results, sample),

            "results": results[:5]  # keep top results for analysis
        }

    # ─────────────────────────────────────────────────────────

    def evaluate_dataset(self, dataset_path):
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        all_results = []

        for sample in dataset:
            res = self.evaluate_query(sample)
            all_results.append(res)

        return all_results