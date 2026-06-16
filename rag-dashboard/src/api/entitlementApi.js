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
export const isEntitlementComplete = (res) => res && res.status === "COMPLETED";
export const reconfirmEligibility = async () => ({ success: true });
export const fetchApplicationGuidance = async () => ({ steps: ["Step 1"] });
export const submitApplication = async () => ({ success: true });
export const fetchApplicationStatus = async () => ({ status: "Pending" });
export const fetchAuditLogs = async () => ({ logs: [] });
