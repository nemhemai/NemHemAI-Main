import logging
from typing import Optional

from app.agents.verification.schemas.schemas import DecisionRequest, DecisionResponse
from app.agents.verification.core.exceptions import DecisionError
from app.agents.verification.core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Decision thresholds
# ---------------------------------------------------------------------------
CONFIDENCE_APPROVE_THRESHOLD = 0.70   # verification confidence must be >= this
CONFIDENCE_REVIEW_THRESHOLD = 0.45    # below this → REJECTED
FRAUD_HIGH_REJECT = True              # HIGH fraud risk always rejects
FRAUD_MEDIUM_REVIEW = True            # MEDIUM fraud risk forces REVIEW (not APPROVE)

# Decision constants
DECISION_APPROVED = "APPROVED"
DECISION_REJECTED = "REJECTED"
DECISION_REVIEW = "MANUAL_REVIEW"


import uuid

class DecisionService:
    """
    Final Decision Agent.

    Aggregates:
    - Verification result (checks passed/failed, confidence)
    - Fraud detection result (risk level, flags)

    Outputs a final APPROVED / REJECTED / MANUAL_REVIEW decision
    with an overall confidence score.
    """

    @staticmethod
    def decide(verification_result: dict, fraud_result: dict) -> dict:
        service = DecisionService()
        request = DecisionRequest(
            verification_result=verification_result,
            fraud_result=fraud_result
        )
        res = service.decide_request(request)
        return res.model_dump()

    def decide_request(self, request: DecisionRequest) -> DecisionResponse:
        logger.info("Starting decision aggregation")

        try:
            verification = request.verification_result or {}
            fraud = request.fraud_result or {}

            # --- Extract key signals with fallbacks ---
            verify_overall_valid: bool = bool(verification.get("overall_valid", False) or verification.get("verified", False))
            verify_confidence: float = float(verification.get("confidence", 0.0))
            verify_passed: list = verification.get("passed_checks", [])
            verify_failed: list = verification.get("failed_checks", [])

            fraud_risk_level: str = str(fraud.get("risk_level") or fraud.get("fraud_risk") or "UNKNOWN").upper()
            fraud_risk_score: float = float(fraud.get("risk_score") or fraud.get("fraud_score") or 0.0)
            fraud_flags: list = fraud.get("fraud_flags", [])
            face_detected: bool = bool(fraud.get("face_detected", True))

            doc_type: str = str(
                verification.get("doc_type")
                or verification.get("document_type")
                or request.doc_type
                or "UNKNOWN"
            ).upper()

            # --- Decision logic ---
            decision, reasons = self._apply_rules(
                verify_overall_valid=verify_overall_valid,
                verify_confidence=verify_confidence,
                verify_failed=verify_failed,
                fraud_risk_level=fraud_risk_level,
                fraud_flags=fraud_flags,
                face_detected=face_detected,
            )

            # --- Combined confidence ---
            combined_confidence = self._compute_combined_confidence(
                verify_confidence=verify_confidence,
                fraud_risk_score=fraud_risk_score,
                decision=decision,
            )

            logger.info(
                f"Decision: {decision} | confidence={combined_confidence:.4f} | "
                f"fraud_risk={fraud_risk_level} | reasons={reasons}"
            )

            return DecisionResponse(
                request_id=str(uuid.uuid4()),
                verified=verify_overall_valid and decision == DECISION_APPROVED,
                confidence=round(combined_confidence, 4),
                fraud_risk=fraud_risk_level,
                decision=decision,
                status="SUCCESS",
                reasons=reasons,
                passed_checks=verify_passed,
                failed_checks=verify_failed,
                fraud_flags=fraud_flags,
                doc_type=doc_type,
                success=True
            )

        except Exception as e:
            logger.error(f"Decision error: {e}", exc_info=True)
            raise DecisionError(f"Decision agent failed: {str(e)}")

    # ------------------------------------------------------------------
    # Rule engine
    # ------------------------------------------------------------------

    def _apply_rules(
        self,
        verify_overall_valid: bool,
        verify_confidence: float,
        verify_failed: list,
        fraud_risk_level: str,
        fraud_flags: list,
        face_detected: bool,
    ) -> tuple[str, list]:
        reasons = []

        # Rule 1: HIGH fraud risk → always REJECT
        if FRAUD_HIGH_REJECT and fraud_risk_level == "HIGH":
            reasons.append(f"Fraud risk is HIGH (flags: {', '.join(fraud_flags)})")
            return DECISION_REJECTED, reasons

        # Rule 2: No face detected → REJECT for photo-bearing documents
        if not face_detected and "NO_FACE_DETECTED" in fraud_flags:
            reasons.append("No face detected in document image")
            return DECISION_REJECTED, reasons

        # Rule 3: Critical verification checks failed → REJECT
        critical_fails = [f for f in verify_failed if self._is_critical_check(f)]
        if critical_fails:
            reasons.append(f"Critical checks failed: {', '.join(critical_fails)}")
            return DECISION_REJECTED, reasons

        # Rule 4: Verification confidence below minimum → REJECT
        if verify_confidence < CONFIDENCE_REVIEW_THRESHOLD:
            reasons.append(
                f"Verification confidence {verify_confidence:.2f} below minimum "
                f"{CONFIDENCE_REVIEW_THRESHOLD}"
            )
            return DECISION_REJECTED, reasons

        # Rule 5: MEDIUM fraud risk + verification confidence below 0.80 → MANUAL_REVIEW
        # If verification is strong (>= 0.80), allow approval despite MEDIUM image quality
        if FRAUD_MEDIUM_REVIEW and fraud_risk_level == "MEDIUM" and verify_confidence < 0.80:
            reasons.append(
                f"Fraud risk is MEDIUM with insufficient verification confidence "
                f"{verify_confidence:.2f} (flags: {', '.join(fraud_flags)})"
            )
            return DECISION_REVIEW, reasons

        # Rule 6: Verification confidence below APPROVE threshold → MANUAL_REVIEW
        if verify_confidence < CONFIDENCE_APPROVE_THRESHOLD:
            reasons.append(
                f"Verification confidence {verify_confidence:.2f} below approval "
                f"threshold {CONFIDENCE_APPROVE_THRESHOLD} — escalating for review"
            )
            return DECISION_REVIEW, reasons

        # Rule 7: Non-critical check failures → MANUAL_REVIEW
        if verify_failed:
            reasons.append(
                f"Some non-critical checks failed: {', '.join(verify_failed)}"
            )
            return DECISION_REVIEW, reasons

        # Rule 8: All clear → APPROVE
        reasons.append("All verification and fraud checks passed")
        return DECISION_APPROVED, reasons

    def _is_critical_check(self, check_name: str) -> bool:
        """
        Checks whose failure causes immediate rejection.
        Non-critical failures route to MANUAL_REVIEW instead.

        Note: dob_valid is intentionally non-critical — DOB parsing can fail
        on unusual formats without indicating a fake document.
        """
        critical = {
            "aadhaar_format",
            "aadhaar_verhoeff_checksum",
            "pan_format",
            "passport_number_format",
            "passport_not_expired",
        }
        return check_name in critical

    # ------------------------------------------------------------------
    # Combined confidence
    # ------------------------------------------------------------------

    def _compute_combined_confidence(
        self,
        verify_confidence: float,
        fraud_risk_score: float,
        decision: str,
    ) -> float:
        """
        Combined confidence = weighted blend of verification confidence
        and inverse fraud risk score.

        When decision is REJECTED the confidence reflects certainty of rejection,
        not trustworthiness of the document.
        """
        # Fraud clean signal: 1.0 = no fraud, 0.0 = high fraud
        fraud_clean = 1.0 - fraud_risk_score

        # Weighted blend (verification 60%, fraud 40%)
        combined = 0.60 * verify_confidence + 0.40 * fraud_clean

        # Cap based on decision
        if decision == DECISION_APPROVED:
            return min(combined, 0.99)
        if decision == DECISION_REJECTED:
            return max(1.0 - combined, 0.01)
        # MANUAL_REVIEW — return as-is
        return combined
