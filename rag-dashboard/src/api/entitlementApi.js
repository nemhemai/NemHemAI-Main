const API_BASE = "http://localhost:8000/api/v1";

export const submitEntitlementQuery = async (queryData) => {
  const response = await fetch(`${API_BASE}/entitlement`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(queryData)
  });
  if (!response.ok) throw new Error("Failed to submit query");
  return response.json();
};

export const fetchEntitlementResult = async (query_id) => {
  const response = await fetch(`${API_BASE}/entitlement/${query_id}`);
  if (!response.ok) throw new Error("Failed to fetch result");
  return response.json();
};

export const verifyDocument = async (formData) => {
  const response = await fetch(`${API_BASE}/verification/verify-pipeline`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) throw new Error("Verification failed");
  return response.json();
};

export const registerCitizen = async (data) => ({ success: true, citizen_id: "CIT-" + Date.now() });
export const fetchCitizenProfile = async (id) => ({ id, name: "John Doe" });
export const updateCitizenProfile = async (id, data) => ({ success: true });
export const isEntitlementComplete = (res) => res && (res.status === "COMPLETED" || res.status === "FAILED");
export const reconfirmEligibility = async (data) => {
  const isApproved = data?.verificationStatus === "APPROVED";
  return {
    success: true,
    overall_decision: isApproved ? "VERIFIED_AND_ELIGIBLE" : "VERIFICATION_FAILED_NOT_ELIGIBLE",
    schemes: [
      {
        scheme_name: "Mock Scheme",
        preliminary_verdict: "ELIGIBLE",
        verification_check: isApproved ? "PASSED" : "FAILED",
        final_decision: isApproved ? "ELIGIBLE" : "NOT_ELIGIBLE"
      }
    ]
  };
};
export const fetchApplicationGuidance = async () => ({ steps: ["Step 1"] });
export const submitApplication = async () => ({ success: true });
export const fetchApplicationStatus = async () => ({ status: "Pending" });

// GACA Integration Endpoints
export const fetchAuditLogs = async (citizenId) => {
  const response = await fetch(`${API_BASE}/gaca/decisions/citizen/${citizenId}`);
  if (!response.ok) throw new Error("Failed to fetch audit logs");
  return response.json();
};

export const fetchDecisionExplanation = async (decisionId) => {
  const encodedDecisionId = encodeURIComponent(decisionId);
  const response = await fetch(`${API_BASE}/gaca/explain/${encodedDecisionId}`);
  if (!response.ok) throw new Error("Failed to fetch decision explanation");
  return response.json();
};
