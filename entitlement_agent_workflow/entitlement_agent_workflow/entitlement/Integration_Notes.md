# Integration Notes

This document provides a comprehensive mapping of how the React UI components interact with the FastAPI backend endpoints. 

## 1. Persona Switcher & Authentication
**React Component:** `Persona Switcher (Header)`
**Action:** User selects a role (CITIZEN, OFFICER, ADMIN) from the dropdown.
**Backend Endpoint:** `POST /api/auth/login`
**Integration Flow:**
- The frontend sends a login request with predefined mock credentials for the selected persona.
- The backend returns an RS256 signed JWT via the `KeycloakValidator` mock.
- The frontend stores this token and uses it as a Bearer token in the `Authorization` header for all subsequent API requests.

## 2. Dashboard Cards & Eligibility Evaluation
**React Component:** `Evaluation Dashboard (Citizen View)`
**Action:** Citizen inputs their profile details or uses the mock loaded profile.
**Backend Endpoint:** `POST /api/v1/entitlement/evaluate`
**Integration Flow:**
- The frontend submits the Citizen 360 Profile and natural language query.
- The backend processes the request through the LLM orchestration pipeline (`PraisonAI`), doing dual-retrieval (Qdrant & Neo4j).
- The returned data populates the **Optimized Benefit Plan**, ranking schemes by readiness, benefit amount, and processing time.

## 3. Dynamic Citations & Scheme Guidance
**React Component:** `Scheme Details & Citations View`
**Action:** User clicks on a specific scheme to view details, missing documents, or official guidelines.
**Backend Endpoint:** `GET /api/v1/citizen/{citizen_id}/guidance/{scheme_id}`
**Integration Flow:**
- The backend dynamically loads the corresponding YAML metadata file and links it to the original PDF source document.
- The frontend displays the specific excerpt, processing days, and a link to the official application portal.

## 4. Bulk Analytics & Insights
**React Component:** `BulkIngestionDashboard`
**Action:** Officer or Admin views system-wide statistics.
**Backend Endpoint:** `GET /api/v1/officer/insights` & `GET /api/v1/officer/applications`
**Integration Flow:**
- The frontend requests system metrics (e.g., total applications, approval rates).
- The backend queries Neo4j/PostgreSQL to aggregate the data and returns statistical payloads.
- Role-based Access Control (RBAC) ensures only `OFFICER` or `ADMIN` roles can successfully fetch this data.

## 5. Application Status Tracking
**React Component:** `Application Tracker`
**Action:** Citizen checks the status of an ongoing application.
**Backend Endpoint:** `GET /api/v1/application/{application_id}/status`
**Integration Flow:**
- The frontend polls or requests the status of a specific application.
- The backend returns the current stage (e.g., "Document Verification") and estimated completion time.
