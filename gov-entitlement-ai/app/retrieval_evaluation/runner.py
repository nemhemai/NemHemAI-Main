# app/retrieval_evaluation/runner.py

from app.core.database import get_db_conn, release_db_conn
from app.retrieval.retriever import HybridRetriever
from app.retrieval_evaluation.evaluator import RetrievalEvaluator


def run_evaluation(dataset_path):

    conn = get_db_conn()
    retriever = HybridRetriever()
    evaluator = RetrievalEvaluator(retriever, conn)

    try:
        results = evaluator.evaluate_dataset(dataset_path)

        total = len(results)

        avg_top1 = sum(r["top1"] for r in results) / total
        avg_top3 = sum(r["top3"] for r in results) / total
        avg_p5   = sum(r["p_at_5"] for r in results) / total
        avg_mrr  = sum(r["mrr"] for r in results) / total

        print("\n================ EVALUATION RESULTS ================")
        print(f"Total Queries : {total}")
        print(f"Top-1 Accuracy: {avg_top1:.3f}")
        print(f"Top-3 Accuracy: {avg_top3:.3f}")
        print(f"Precision@5   : {avg_p5:.3f}")
        print(f"MRR           : {avg_mrr:.3f}")

        return results

    finally:
        release_db_conn(conn)


if __name__ == "__main__":
    run_evaluation("app/retrieval_evaluation/evaluation_dataset.json")