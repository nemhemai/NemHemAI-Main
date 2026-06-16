# app/retrieval_evaluation/analysis.py

def get_failures(results):
    return [r for r in results if r["top1"] == 0]


def categorize_failure(result):
    query = result["query"].lower()

    if "penalty" in query:
        return "enforcement_failure"

    if "define" in query or "what is" in query:
        return "definition_failure"

    if "how much" in query or "limits" in query:
        return "table_failure"

    return "general_failure"