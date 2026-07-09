import os
from typing import List, Dict, Any, Tuple

class OpenHumanContext:
    """
    OpenHuman Context Layer for local intent modeling, edge case detection, 
    proactive document prompts, and role-based tone adaptation.
    """

    def __init__(self):
        # Local session-based memory tree: {session_id: {"history": [], "profile": dict}}
        self._memory_tree: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Fetch or initialize a session node in the Memory Tree."""
        if session_id not in self._memory_tree:
            self._memory_tree[session_id] = {
                "history": [],
                "profile": {},
                "last_evaluations": {}
            }
        return self._memory_tree[session_id]

    def add_interaction(self, session_id: str, query: str, response: str):
        """Saves a query-response pair in the session's interaction log."""
        session = self.get_or_create_session(session_id)
        session["history"].append({"query": query, "response": response})

    def detect_intent(self, session_id: str, current_query: str) -> str:
        """
        Analyzes conversation history and current query to identify user intent:
        - REPEAT_QUERY: If the user repeats the same query.
        - CONFUSED: Vague queries or request for help.
        - MISSING_DOCS: Inquiries about documents or missing certificates.
        - GENERAL_INQUIRY: Standard scheme/eligibility checks.
        """
        session = self.get_or_create_session(session_id)
        history = session["history"]
        query_lower = current_query.lower().strip()

        # 1. Check for Repeat Query
        for interaction in history:
            prev_query = interaction["query"].lower().strip()
            # If queries are identical or close substrings
            if query_lower == prev_query or (len(query_lower) > 5 and query_lower in prev_query) or (len(prev_query) > 5 and prev_query in query_lower):
                return "REPEAT_QUERY"

        # 2. Check for Document queries
        doc_keywords = ["document", "certificate", "proof", "aadhaar", "passbook", "ration", "caste", "vending", "missing", "verify"]
        if any(kw in query_lower for kw in doc_keywords):
            return "MISSING_DOCS"

        # 3. Check for Confused State
        confused_keywords = ["help", "confused", "vague", "dont know", "don't know", "how do i", "what is", "clueless", "lost", "explain"]
        if any(kw in query_lower for kw in confused_keywords) or len(query_lower.split()) <= 2:
            return "CONFUSED"

        return "GENERAL_INQUIRY"

    def detect_edge_cases(self, evaluation_report: dict) -> Tuple[dict, List[str]]:
        """
        Inspects evaluated schemes in the pipeline report.
        If a scheme's status is PENDING_DOCS and it has EXACTLY one missing document:
        - Promotes the status to LIKELY_ELIGIBLE.
        - Generates a proactive missing document prompt.
        
        Returns the updated evaluation report and a list of proactive prompts.
        """
        proactive_prompts = []
        schemes_evaluated = evaluation_report.get("schemes_evaluated", {})

        for scheme_id, eval_data in schemes_evaluated.items():
            status = eval_data.get("final_status")
            missing_docs = eval_data.get("missing_documents", [])
            scheme_name = eval_data.get("scheme_name", scheme_id)

            # Check for PENDING_DOCS edge case with exactly one missing document
            if status == "PENDING_DOCS" and len(missing_docs) == 1:
                missing_doc = missing_docs[0]
                # Promote status to LIKELY_ELIGIBLE
                eval_data["final_status"] = "LIKELY_ELIGIBLE"
                # Add proactive alert
                alert = f"You qualify for '{scheme_name}' but need to verify your {missing_doc}."
                eval_data["proactive_prompt"] = alert
                proactive_prompts.append(alert)

        return evaluation_report, proactive_prompts

    def get_tone_instructions(self, role: str) -> str:
        """
        Returns persona formatting instructions to shape the LLM response.
        - CITIZEN: Empathetic, jargon-free, simple language.
        - OFFICER: Detailed, technical audit trail, policy contexts.
        - ADMIN: System-level, metrics, logs metadata validator.
        """
        role_upper = role.upper()
        if role_upper == "CITIZEN":
            return (
                "Write in citizen-friendly, warm, empathetic language. "
                "Do NOT use legal or database jargon (like 'eq', 'gte', or 'detaching'). "
                "Keep sentences simple. List the matching schemes and highlight the next steps "
                "needed, especially focusing on missing documents."
            )
        elif role_upper == "OFFICER":
            return (
                "Write in a highly formal, professional, policy-oriented tone. "
                "Include detailed evaluation summaries, including specific operators (eq, lte, between), "
                "exact criteria parameters, database sources, audit trails, and policy-relevant context "
                "suitable for backend verification processing."
            )
        elif role_upper == "ADMIN":
            return (
                "Write a concise system administration summary. "
                "Highlight system resource states, rule counts processed, schema validation statuses, "
                "and vector retrieval metrics."
            )
        else:
            # Default fallback
            return "Write in a clear, professional, informative tone."
