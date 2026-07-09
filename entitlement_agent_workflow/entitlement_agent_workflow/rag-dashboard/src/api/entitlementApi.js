import authAxios from "../utils/authAxios";

export const submitEntitlementQuery = async (queryData) => {
  const response = await authAxios.post("/api/v1/entitlement", queryData);
  return response.data;
};

export const fetchEntitlementResult = async (query_id) => {
  const response = await authAxios.get(`/api/v1/entitlement/${query_id}`);
  return response.data;
};

export const verifyDocument = async (formData) => {
  const response = await authAxios.post("/api/v1/verification/verify-pipeline", formData);
  return response.data;
};

export const registerCitizen = async (data) => {
  const response = await authAxios.post("/api/v1/citizen/register", {
    mobile_number: data.mobileNumber,
    aadhaar_id: data.aadhaarId,
    email: data.email
  });
  return response.data;
};

export const fetchCitizenProfile = async (id) => {
  const response = await authAxios.get(`/api/v1/citizen/${id}/profile`);
  return response.data;
};

export const updateCitizenProfile = async (id, data) => {
  const response = await authAxios.put(`/api/v1/citizen/${id}/profile`, {
    personal_info: data.personalInfo,
    household_info: data.householdInfo,
    socio_economic_info: data.socioEconomicInfo,
    existing_benefits: data.existingBenefits || []
  });
  return response.data;
};

export const isEntitlementComplete = (res) => res && res.status === "COMPLETED";

export const reconfirmEligibility = async (data) => {
  const response = await authAxios.post("/api/v1/verification/reconfirm", {
    citizen_id: data.citizenId
  });
  return response.data;
};

export const fetchApplicationGuidance = async (data) => {
  const response = await authAxios.get("/api/v1/application/guide", {
    params: {
      citizen_id: data.citizenId,
      scheme_name: data.schemeName
    }
  });
  return response.data;
};

export const submitApplication = async (data) => {
  const response = await authAxios.post("/api/v1/application/submit", {
    citizen_id: data.citizenId,
    scheme_name: data.schemeName,
    channel: data.channel
  });
  return response.data;
};

export const fetchApplicationStatus = async (application_id) => {
  const response = await authAxios.get(`/api/v1/application/${application_id}/status`);
  return response.data;
};

export const fetchAuditLogs = async (citizen_id) => {
  const response = await authAxios.get(`/api/v1/audit/logs/${citizen_id}`);
  return response.data;
};
