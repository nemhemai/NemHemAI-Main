
import React, { useState, useEffect, useCallback } from "react";
import {
  registerCitizen,
  fetchCitizenProfile,
  updateCitizenProfile,
  submitEntitlementQuery,
  fetchEntitlementResult,
  isEntitlementComplete,
  verifyDocument,
  reconfirmEligibility,
  fetchApplicationGuidance,
  submitApplication,
  fetchApplicationStatus,
  fetchAuditLogs,
  fetchDecisionExplanation
} from "../api/entitlementApi";

// Verhoeff algorithm tables for validation check
const VERHOEFF_D = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
  [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
  [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
  [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
  [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
  [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
  [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
  [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
  [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
];

const VERHOEFF_P = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
  [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
  [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
  [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
  [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
  [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
  [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
];

const validateVerhoeff = (str) => {
  if (!str || typeof str !== "string" || !/^\d+$/.test(str)) return false;
  let c = 0;
  const len = str.length;
  for (let i = 0; i < len; i++) {
    const pIndex = i % 8;
    const digit = parseInt(str.charAt(len - 1 - i), 10);
    c = VERHOEFF_D[c][VERHOEFF_P[pIndex][digit]];
  }
  return c === 0;
};

const getFriendlyCondition = (label) => {
  const mapping = {
    // PM-KISAN
    "Applicant is a farmer": "Farmer",
    "Applicant has cultivable land ownership": "Land Owner",
    "Aadhaar is available/seeded": "Aadhaar Status",
    "Bank account is available": "Bank Account Details",
    "has_aadhaar": "Aadhaar Status",
    "has_bank_account": "Bank Account Details",
    "Aadhaar Status": "Aadhaar Status",
    "Bank Account Details": "Bank Account Details",
    // PM SVANidhi
    "Applicant is a street vendor": "Street vendor occupation",
    "Annual income is within PM SVANidhi limits": "Income within limit",
    "Applicant is in an urban area": "Urban applicant",
    "Vending certificate or ULB/TVC recommendation is available": "Vending Certificate / ULB Recommendation",
    "has_vending_certificate": "Vending Certificate",
    // PMAY-U
    "Household does not own a pucca house": "No Pucca House",
    "Annual income is within PMAY-U income bands": "Income within limit",
    "has_pucca_house": "Pucca House Ownership Status",
    "Pucca House Ownership Status": "Pucca House Ownership Status",
    // PM Awas Yojana
    "Applicant is in a rural area": "Rural Resident",
    "Government employee exclusion": "Government Employee check",
    "Income tax payer exclusion": "Income Tax Payer check",
    "Motorized vehicle ownership exclusion": "Motorized Vehicle check",
    // PM-KUSUM
    "Applicant has cultivable land for solar pump/plant use": "Land Owner",
    "land_ownership_acres": "Land Ownership Information",
    "Land Ownership Information": "Land Ownership Information",
    // Post-Matric Scholarship
    "Applicant is enrolled in a post-matric course": "Post-Matric Student",
    "Applicant belongs to SC, ST, or OBC category": "Category SC/ST/OBC",
    "Parental/household income is within category threshold": "Income within limit",
  };
  return mapping[label] || label;
};

const getFriendlyMissing = (field) => {
  const mapping = {
    "Aadhaar status": "Aadhaar linkage status",
    "Aadhaar Status": "Aadhaar linkage status",
    "has_aadhaar": "Aadhaar linkage status",
    "Bank account details": "Bank account verification",
    "Bank Account Details": "Bank account verification",
    "has_bank_account": "Bank account verification",
    "Vending certificate": "Vending Certificate",
    "has_vending_certificate": "Vending Certificate",
    "ULB/TVC recommendation letter": "ULB Recommendation",
    "has_ulb_recommendation": "ULB Recommendation",
    "Land ownership information": "Land Ownership Records",
    "Land Ownership Information": "Land Ownership Records",
    "land_ownership_acres": "Land Ownership Records",
    "Annual income": "Income Certificate",
    "income_annual": "Income Certificate",
    "Pucca house ownership": "Pucca house ownership status",
    "Pucca House Ownership Status": "Pucca house ownership status",
    "has_pucca_house": "Pucca house ownership status",
  };
  return mapping[field] || field;
};

const getFriendlyDocument = (doc) => {
  const mapping = {
    "Bank account details": "Bank Passbook",
    "Bank Account Details": "Bank Passbook",
    "has_bank_account": "Bank Passbook",
    "Vending certificate or ULB/TVC recommendation": "Vending Certificate / TVC Recommendation",
    "has_vending_certificate": "Vending Certificate / TVC Recommendation",
    "Income certificate": "Income Certificate",
    "income_annual": "Income Certificate",
    "No-pucca-house declaration": "No-Pucca-House Declaration",
    "has_pucca_house": "No-Pucca-House Declaration",
    "Aadhaar": "Aadhaar",
    "has_aadhaar": "Aadhaar",
    "Land records": "Land Records",
    "land_ownership_acres": "Land Records",
    "Bank passbook": "Bank Passbook",
  };
  return mapping[doc] || doc;
};


function EntitlementDashboard() {
  // Navigation tabs
  const [activeTab, setActiveTab] = useState("onboarding");
  const [expandedSchemes, setExpandedSchemes] = useState({});

  const toggleSchemeDetails = (schemeName) => {
    setExpandedSchemes((prev) => ({
      ...prev,
      [schemeName]: !prev[schemeName]
    }));
  };


  // Global state
  const [citizenId, setCitizenId] = useState("");
  const [citizenProfile, setCitizenProfile] = useState(null);
  const [eligibilityContext, setEligibilityContext] = useState(null);
  
  // Registration Form (Step 1 & 2)
  const [regMobile, setRegMobile] = useState("");
  const [regAadhaar, setRegAadhaar] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regLoading, setRegLoading] = useState(false);
  const [regMessage, setRegMessage] = useState("");
  const [regSuccess, setRegSuccess] = useState(false);

  // Live Focus States for Validation Checklists
  const [mobileFocused, setMobileFocused] = useState(false);
  const [aadhaarFocused, setAadhaarFocused] = useState(false);
  const [emailFocused, setEmailFocused] = useState(false);

  // Checklist Style Helper
  const validationChecklistStyle = {
    marginTop: "8px",
    padding: "10px 14px",
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    fontSize: "12px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
  };

  const validationItemStyle = (passed) => ({
    color: passed ? "#166534" : "#991b1b",
    fontWeight: "600",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    transition: "color 0.2s ease"
  });

  const mobileValidations = {
    length: regMobile.length === 10,
    numeric: /^\d+$/.test(regMobile),
    prefix: /^[6-9]/.test(regMobile)
  };

  const isMobileEmpty = regMobile === "";
  const allMobilePassed = mobileValidations.length && mobileValidations.numeric && mobileValidations.prefix;
  const showMobileChecklist = !mobileFocused && !isMobileEmpty && !allMobilePassed;

  const aadhaarValidations = {
    length: regAadhaar.length === 12,
    numeric: /^\d+$/.test(regAadhaar),
    prefix: regAadhaar.length > 0 && regAadhaar.charAt(0) !== '0' && regAadhaar.charAt(0) !== '1',
    verhoeff: validateVerhoeff(regAadhaar)
  };

  const isAadhaarEmpty = regAadhaar === "";
  const allAadhaarPassed = aadhaarValidations.length && aadhaarValidations.numeric && aadhaarValidations.prefix && aadhaarValidations.verhoeff;
  const showAadhaarChecklist = !aadhaarFocused && !isAadhaarEmpty && !allAadhaarPassed;

  const emailValidations = {
    validOrEmpty: regEmail === "" || /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(regEmail)
  };

  const isEmailEmpty = regEmail === "";
  const allEmailPassed = emailValidations.validOrEmpty;
  const showEmailChecklist = !emailFocused && !isEmailEmpty && !allEmailPassed;

  // Profile Form (Step 3 & 4)
  const [name, setName] = useState("");
  const [stateName, setStateName] = useState("Maharashtra");
  const [urbanRural, setUrbanRural] = useState("urban");
  const [income, setIncome] = useState(250000);
  const [occupation, setOccupation] = useState("street_vendor");
  const [category, setCategory] = useState("OBC");
  const [landAcres, setLandAcres] = useState(0);
  const [hasPuccaHouse, setHasPuccaHouse] = useState(false);
  const [dependents, setDependents] = useState(2);
  const [hasSeniors, setHasSeniors] = useState(false);
  const [hasStudents, setHasStudents] = useState(true);
  const [hasWidows, setHasWidows] = useState(false);
  const [disability, setDisability] = useState(false);
  const [education, setEducation] = useState("post_matric");
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileMsg, setProfileMsg] = useState("");

  // RAG / Discovery Check (Step 5 & 6)
  const [rawQuery, setRawQuery] = useState("");
  const [checkLoading, setCheckLoading] = useState(false);
  const [checkResult, setCheckResult] = useState(null);
  const [checkError, setCheckError] = useState("");

  // Verification Agent (Step 7 & 8)
  const [docType, setDocType] = useState("Income Certificate");
  const [file, setFile] = useState(null);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verificationPipelineLogs, setVerificationPipelineLogs] = useState(null);
  const [reconfirmResult, setReconfirmResult] = useState(null);

  // Application Guidance & Submissions (Step 11-13)
  const [selectedScheme, setSelectedScheme] = useState("PM SVANidhi");
  const [guidanceData, setGuidanceData] = useState(null);
  const [guidanceLoading, setGuidanceLoading] = useState(false);
  const [submittingApp, setSubmittingApp] = useState(false);
  const [submissionResult, setSubmissionResult] = useState(null);
  const [trackingId, setTrackingId] = useState("");
  const [trackingResult, setTrackingResult] = useState(null);
  const [trackingLoading, setTrackingLoading] = useState(false);

  // Audit Logs (Step 14)
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const [explanationModal, setExplanationModal] = useState({ isOpen: false, data: null, loading: false, error: null });

  const handleOpenExplanation = async (decisionId) => {
    setExplanationModal({ isOpen: true, data: null, loading: true, error: null });
    try {
      const data = await fetchDecisionExplanation(decisionId);
      setExplanationModal({ isOpen: true, data, loading: false, error: null });
    } catch (err) {
      setExplanationModal({ isOpen: true, data: null, loading: false, error: err.message });
    }
  };

  // Fetch audit logs when citizenId changes or when tab opens
  const loadAuditLogs = useCallback(async () => {
    if (!citizenId) return;
    setAuditLoading(true);
    try {
      const response = await fetchAuditLogs(citizenId);
      setAuditLogs(Array.isArray(response) ? response : (response?.logs || []));
    } catch (err) {
      console.error(err);
    } finally {
      setAuditLoading(false);
    }
  }, [citizenId]);

  useEffect(() => {
    if (activeTab === "audit" && citizenId) {
      loadAuditLogs();
    }
  }, [activeTab, citizenId, loadAuditLogs]);

  const generateQueryFromProfile = useCallback(() => {
    const occLabel = occupation === "street_vendor" 
      ? "street vendor" 
      : (occupation === "farmer" ? "farmer" : (occupation === "student" ? "student" : (occupation === "artisan" ? "artisan" : "applicant")));
    let q = `I am a ${occLabel} living in a ${urbanRural} area of ${stateName}. `;
    q += `I belong to the ${category} category, with an annual household income of ₹${income}. `;
    if (parseFloat(landAcres) > 0) {
      q += `I own ${landAcres} acres of cultivable land. `;
    }
    if (disability) {
      q += `I have a disability status. `;
    }
    if (hasPuccaHouse) {
      q += `I own a pucca house. `;
    } else {
      q += `I do not own a pucca house. `;
    }
    if (hasStudents) {
      q += `My household includes students. `;
    }
    if (hasSeniors) {
      q += `My household includes senior citizens. `;
    }
    if (hasWidows) {
      q += `My household includes widows. `;
    }
    q += `I need support and welfare benefits.`;
    return q;
  }, [occupation, urbanRural, stateName, category, income, landAcres, disability, hasPuccaHouse, hasStudents, hasSeniors, hasWidows]);

  useEffect(() => {
    setRawQuery(generateQueryFromProfile());
  }, [generateQueryFromProfile]);

  // Handle Registration
  const handleRegister = async () => {
    if (!regMobile || !regAadhaar) {
      setRegMessage("Mobile and Aadhaar are required.");
      setRegSuccess(false);
      return;
    }

    // Mobile validation: exactly 10 digits
    const mobilePattern = /^[6-9]\d{9}$/;
    if (!mobilePattern.test(regMobile)) {
      setRegMessage("Mobile number must be a 10-digit numeric code starting with 6, 7, 8, or 9.");
      setRegSuccess(false);
      return;
    }

    // Aadhaar validation: exactly 12 digits, numeric only, first digit not 0 or 1, verhoeff validation
    if (!/^\d+$/.test(regAadhaar)) {
      setRegMessage("Aadhaar ID must be numeric only.");
      setRegSuccess(false);
      return;
    }

    if (regAadhaar.length !== 12) {
      setRegMessage("Aadhaar ID must be exactly 12 digits.");
      setRegSuccess(false);
      return;
    }

    if (regAadhaar.charAt(0) === '0' || regAadhaar.charAt(0) === '1') {
      setRegMessage("Aadhaar ID first digit cannot be 0 or 1.");
      setRegSuccess(false);
      return;
    }

    if (!validateVerhoeff(regAadhaar)) {
      console.warn("Aadhaar ID failed Verhoeff checksum validation, but continuing for demo purposes.");
    }

    // Email validation (optional): valid format
    if (regEmail) {
      const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      if (!emailPattern.test(regEmail)) {
        setRegMessage("Please enter a valid email address.");
        setRegSuccess(false);
        return;
      }
    }

    setRegLoading(true);
    setRegMessage("");
    try {
      const res = await registerCitizen({
        mobileNumber: regMobile,
        aadhaarId: regAadhaar,
        email: regEmail || null
      });
      if (res.success) {
        setCitizenId(res.citizen_id);
        setRegSuccess(true);
        setRegMessage(res.message);
        // Load profile next
        const profileRes = await fetchCitizenProfile(res.citizen_id);
        setCitizenProfile(profileRes);
        // Pre-fill profile state
        setName(profileRes?.personal_info?.name || profileRes?.name || "");
        setActiveTab("profile");
      } else {
        setRegMessage(res.message);
      }
    } catch (err) {
      setRegMessage(err.response?.data?.detail || err.message || "Registration failed");
    } finally {
      setRegLoading(false);
    }
  };

  // Handle Profile Update
  const handleProfileUpdate = async () => {
    if (!citizenId) {
      setProfileMsg("Please register/verify citizen first.");
      return;
    }

    if (!name.trim()) {
      setProfileMsg("Full Name is required.");
      return;
    }

    if (!stateName.trim()) {
      setProfileMsg("State Residency is required.");
      return;
    }

    const incomeVal = parseFloat(income);
    if (isNaN(incomeVal) || incomeVal < 0) {
      setProfileMsg("Annual Household Income must be a non-negative number.");
      return;
    }

    const dependentsVal = parseInt(dependents);
    if (isNaN(dependentsVal) || dependentsVal < 0) {
      setProfileMsg("Household Dependents Count must be a non-negative number.");
      return;
    }

    const landAcresVal = parseFloat(landAcres);
    if (isNaN(landAcresVal) || landAcresVal < 0) {
      setProfileMsg("Land Ownership must be a non-negative number.");
      return;
    }

    setProfileLoading(true);
    setProfileMsg("");
    try {
      const personal = { name: name.trim(), state: stateName.trim(), urban_rural: urbanRural };
      const household = { dependents_count: dependentsVal, has_senior_citizens: hasSeniors, has_students: hasStudents, has_widows: hasWidows };
      const socio = { income_annual: incomeVal, occupation, category, land_ownership_acres: landAcresVal, has_pucca_house: hasPuccaHouse, disability_status: disability, education_level: education };
      
      const res = await updateCitizenProfile(citizenId, {
        personalInfo: personal,
        householdInfo: household,
        socioEconomicInfo: socio
      });
      
      setCitizenProfile(res.profile_360);
      setEligibilityContext(res.eligibility_context_model);
      setProfileMsg("Citizen 360 Profile and Socio-Economic Assessment context successfully created!");
      setRawQuery(generateQueryFromProfile());
      setActiveTab("discovery");
    } catch (err) {
      setProfileMsg(err.response?.data?.detail || err.message || "Profile update failed");
    } finally {
      setProfileLoading(false);
    }
  };

  // Run Entitlement discovery query
  const handleEntitlementCheck = async () => {
    if (!rawQuery.trim()) {
      setCheckError("Query cannot be empty");
      return;
    }
    setCheckLoading(true);
    setCheckError("");
    setCheckResult(null);

    try {
      const queued = await submitEntitlementQuery({
        citizen_id: citizenId || null,
        raw_query: rawQuery
      });

      let current = null;
      let loadedInitial = false;

      // Poll up to 300 times (every 1 second = 5 minutes total)
      for (let attempt = 0; attempt < 300; attempt += 1) {
        current = await fetchEntitlementResult(queued.query_id);

        if (current?.status === "GENERATING_EXPLANATION") {
          if (!loadedInitial) {
            setCheckResult(current);
            setCheckLoading(false); // Hide full page spinner
            loadedInitial = true;
          }
        }

        if (isEntitlementComplete(current)) {
          setCheckResult(current);
          setCheckLoading(false);
          // Auto-advance to the next tab after 3 seconds so the user can briefly see the results
          setTimeout(() => {
            setActiveTab("verification");
          }, 3000);
          break;
        }

        await new Promise((resolve) => setTimeout(resolve, 1000));
      }

      if (!isEntitlementComplete(current) && !loadedInitial) {
        throw new Error("Entitlement check timeout. Refresh shortly.");
      }
    } catch (err) {
      setCheckError(err.response?.data?.detail || err.message || "Check failed");
    } finally {
      setCheckLoading(false);
    }
  };

  // Document Verification Agent trigger
  const handleVerifyDocument = async () => {
    if (!citizenId) {
      alert("Please verify/onboard a citizen first.");
      return;
    }
    if (!file) {
      alert("Please select a document file.");
      return;
    }
    setVerifyLoading(true);
    setVerificationPipelineLogs(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const log = await verifyDocument(formData);
      setVerificationPipelineLogs(log);
    } catch (err) {
      alert(err.message);
    } finally {
      setVerifyLoading(false);
    }
  };

  // Run reconfirmation
  const handleReconfirm = async () => {
    if (!citizenId) return;
    try {
      const res = await reconfirmEligibility({ citizenId });
      setReconfirmResult(res);
    } catch (err) {
      alert(err.message);
    }
  };

  // Fetch Guidance
  const handleFetchGuidance = async () => {
    if (!citizenId) return;
    setGuidanceLoading(true);
    setGuidanceData(null);
    setSubmissionResult(null);
    try {
      const data = await fetchApplicationGuidance({
        citizenId,
        schemeName: selectedScheme
      });
      setGuidanceData(data);
    } catch (err) {
      alert(err.message);
    } finally {
      setGuidanceLoading(false);
    }
  };

  // Submit application
  const handleAppSubmit = async (channel) => {
    if (!citizenId || !guidanceData) return;
    setSubmittingApp(true);
    try {
      const res = await submitApplication({
        citizenId,
        schemeName: selectedScheme,
        formData: guidanceData.prefilled_form,
        submissionChannel: channel
      });
      setSubmissionResult(res);
      setTrackingId(res.application_id);
      setTrackingResult(res);
      setActiveTab("audit");
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmittingApp(false);
    }
  };

  // Live status track
  const handleTrackStatus = async () => {
    if (!trackingId.trim()) {
      alert("Application or Tracking ID is required.");
      return;
    }
    setTrackingLoading(true);
    try {
      const res = await fetchApplicationStatus(trackingId.trim());
      setTrackingResult(res);
    } catch (err) {
      alert(err.message);
    } finally {
      setTrackingLoading(false);
    }
  };

  const checkDetermination = checkResult?.determination || {};

  return (
    <div style={styles.container}>
      {/* Visual Premium Header */}
      <header style={styles.header}>
        <div style={styles.headerTextGroup}>
          <h1 style={styles.title}>Unified Citizen Entitlement Agent</h1>
          <p style={styles.subtitle}>
            Stateful Multi-Agent Workflow Orchestrator powering Citizen Registration, Eligibility Assessment, Verification, and Submissions.
          </p>
        </div>
        {citizenId && (
          <div style={styles.activeCitizenChip}>
            <span style={styles.pulseDot}></span>
            <span>Citizen ID: <strong>{citizenId.substring(0,8)}...</strong></span>
            {citizenProfile?.personal_info?.name && (
              <span style={{marginLeft: 12}}>Name: <strong>{citizenProfile.personal_info.name}</strong></span>
            )}
          </div>
        )}
      </header>

      {/* Tabs Stepper */}
      <nav style={styles.tabNav}>
        {[
          { id: "onboarding", label: "1. Onboarding & Verification" },
          { id: "profile", label: "2. Citizen 360 Profile" },
          { id: "discovery", label: "3. Discovery & Optimization" },
          { id: "verification", label: "4. Document Verification" },
          { id: "audit", label: "5. Audit compliance Logs" }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...styles.tabButton,
              ...(activeTab === tab.id ? styles.tabButtonActive : {})
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Panels container */}
      <main style={styles.panelCard}>
        
        {/* Tab 1: Onboarding */}
        {activeTab === "onboarding" && (
          <div style={styles.panelContent}>
            <h2 style={styles.sectionHeading}>Citizen Registration & Identity Verification</h2>
            <p style={styles.infoText}>
              Steps 1 & 2: Enter citizen mobile, Aadhaar, and optional email. Identity verification checks against internal registry indexes.
            </p>
            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Mobile Number *</label>
              <input
                type="text"
                placeholder="e.g. 9876543210"
                value={regMobile}
                onChange={(e) => setRegMobile(e.target.value)}
                onFocus={() => setMobileFocused(true)}
                onBlur={() => setMobileFocused(false)}
                style={styles.formInput}
              />
              {showMobileChecklist && (
                <div style={validationChecklistStyle}>
                  {!mobileValidations.length && (
                    <div style={validationItemStyle(false)}>
                      ✗ 10 digits
                    </div>
                  )}
                  {!mobileValidations.numeric && (
                    <div style={validationItemStyle(false)}>
                      ✗ Numeric only
                    </div>
                  )}
                  {!mobileValidations.prefix && (
                    <div style={validationItemStyle(false)}>
                      ✗ Starts with 6, 7, 8, or 9
                    </div>
                  )}
                </div>
              )}
            </div>
            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Aadhaar / Citizen ID *</label>
              <input
                type="text"
                placeholder="e.g. 234567890124"
                value={regAadhaar}
                onChange={(e) => setRegAadhaar(e.target.value)}
                onFocus={() => setAadhaarFocused(true)}
                onBlur={() => setAadhaarFocused(false)}
                style={styles.formInput}
              />
              {showAadhaarChecklist && (
                <div style={validationChecklistStyle}>
                  {!aadhaarValidations.length && (
                    <div style={validationItemStyle(false)}>
                      ✗ 12 digits
                    </div>
                  )}
                  {!aadhaarValidations.numeric && (
                    <div style={validationItemStyle(false)}>
                      ✗ Numeric only
                    </div>
                  )}
                  {!aadhaarValidations.prefix && (
                    <div style={validationItemStyle(false)}>
                      ✗ First digit not 0 or 1
                    </div>
                  )}
                  {!aadhaarValidations.verhoeff && (
                    <div style={validationItemStyle(false)}>
                      ✗ Verhoeff checksum validation
                    </div>
                  )}
                </div>
              )}
            </div>
            <div style={styles.formGroup}>
              <label style={styles.formLabel}>Email Address (Optional)</label>
              <input
                type="email"
                placeholder="e.g. citizen@gov.in"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                onFocus={() => setEmailFocused(true)}
                onBlur={() => setEmailFocused(false)}
                style={styles.formInput}
              />
              {showEmailChecklist && (
                <div style={validationChecklistStyle}>
                  {!emailValidations.validOrEmpty && (
                    <div style={validationItemStyle(false)}>
                      ✗ Valid email format (optional)
                    </div>
                  )}
                </div>
              )}
            </div>
            <button
              onClick={handleRegister}
              disabled={regLoading}
              style={styles.actionButton}
            >
              {regLoading ? "Running Verification..." : "Verify Identity & Register"}
            </button>
            {regMessage && (
              <div style={regSuccess ? styles.successAlert : styles.errorAlert}>
                {regMessage}
              </div>
            )}
            {regSuccess && (
              <div style={styles.guideToNext}>
                🎉 <strong>Identity Verified!</strong> Proceed to the **Citizen 360 Profile** tab to fill details and build the socio-economic eligibility context model.
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Profile 360 */}
        {activeTab === "profile" && (
          <div style={styles.panelContent}>
            <h2 style={styles.sectionHeading}>Citizen 360 Profile & Socio-Economic Assessment</h2>
            <p style={styles.infoText}>
              Steps 3 & 4: Build a unified profile. The system compiles household and socio-economic markers to build the Eligibility Context Model.
            </p>
            {!citizenId && <div style={styles.warningAlert}>A citizen must be registered first (Tab 1).</div>}
            
            <div style={styles.splitGrid}>
              <div>
                <h3 style={styles.subHeading}>Personal & Household Information</h3>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Full Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>State Residency</label>
                  <input
                    type="text"
                    value={stateName}
                    onChange={(e) => setStateName(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Urban or Rural</label>
                  <select
                    value={urbanRural}
                    onChange={(e) => setUrbanRural(e.target.value)}
                    style={styles.formSelect}
                  >
                    <option value="urban">Urban</option>
                    <option value="rural">Rural</option>
                  </select>
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Household Dependents Count</label>
                  <input
                    type="number"
                    min="0"
                    value={dependents}
                    onChange={(e) => setDependents(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.checkboxContainer}>
                  <input
                    type="checkbox"
                    checked={hasSeniors}
                    onChange={(e) => setHasSeniors(e.target.checked)}
                    id="hasSeniors"
                  />
                  <label htmlFor="hasSeniors" style={styles.checkboxLabel}>Includes Senior Citizens</label>
                </div>
                <div style={styles.checkboxContainer}>
                  <input
                    type="checkbox"
                    checked={hasStudents}
                    onChange={(e) => setHasStudents(e.target.checked)}
                    id="hasStudents"
                  />
                  <label htmlFor="hasStudents" style={styles.checkboxLabel}>Includes Students</label>
                </div>
                <div style={styles.checkboxContainer}>
                  <input
                    type="checkbox"
                    checked={hasWidows}
                    onChange={(e) => setHasWidows(e.target.checked)}
                    id="hasWidows"
                  />
                  <label htmlFor="hasWidows" style={styles.checkboxLabel}>Includes Widows</label>
                </div>
              </div>

              <div>
                <h3 style={styles.subHeading}>Socio-Economic & Assets Assessment</h3>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Annual Household Income (₹)</label>
                  <input
                    type="number"
                    min="0"
                    value={income}
                    onChange={(e) => setIncome(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Occupation</label>
                  <select
                    value={occupation}
                    onChange={(e) => setOccupation(e.target.value)}
                    style={styles.formSelect}
                  >
                    <option value="street_vendor">Street Vendor</option>
                    <option value="farmer">Farmer</option>
                    <option value="student">Student</option>
                    <option value="artisan">Artisan</option>
                    <option value="unemployed">Unemployed</option>
                  </select>
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Caste / Applicant Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    style={styles.formSelect}
                  >
                    <option value="General">General / EWS</option>
                    <option value="OBC">OBC</option>
                    <option value="SC">SC</option>
                    <option value="ST">ST</option>
                  </select>
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Land Ownership (Acres)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={landAcres}
                    onChange={(e) => setLandAcres(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Education Level</label>
                  <select
                    value={education}
                    onChange={(e) => setEducation(e.target.value)}
                    style={styles.formSelect}
                  >
                    <option value="none">Below Class 10</option>
                    <option value="matric">Matric (Class 10)</option>
                    <option value="post_matric">Post-Matric (Class 11, 12, College)</option>
                  </select>
                </div>
                <div style={styles.checkboxContainer}>
                  <input
                    type="checkbox"
                    checked={hasPuccaHouse}
                    onChange={(e) => setHasPuccaHouse(e.target.checked)}
                    id="hasPuccaHouse"
                  />
                  <label htmlFor="hasPuccaHouse" style={styles.checkboxLabel}>Already Owns a Pucca House</label>
                </div>
                <div style={styles.checkboxContainer}>
                  <input
                    type="checkbox"
                    checked={disability}
                    onChange={(e) => setDisability(e.target.checked)}
                    id="disability"
                  />
                  <label htmlFor="disability" style={styles.checkboxLabel}>Has Disability Status</label>
                </div>
              </div>
            </div>

            <button
              onClick={handleProfileUpdate}
              disabled={profileLoading || !citizenId}
              style={styles.actionButton}
            >
              {profileLoading ? "Updating Profile..." : "Update Profile & Run Socio-Economic Assessment"}
            </button>
            {profileMsg && <div style={styles.successAlert}>{profileMsg}</div>}
            
            {eligibilityContext && (
              <div style={styles.assessmentModelCard}>
                <h4 style={styles.cardHeading}>Generated Eligibility Context Model</h4>
                <div style={styles.gridColumns3}>
                  <div style={styles.badgeItem}>
                    <span>BPL/APL Status:</span>
                    <strong>{eligibilityContext.bpl_apl_status}</strong>
                  </div>
                  <div style={styles.badgeItem}>
                    <span>Household Income:</span>
                    <strong>₹{eligibilityContext.household_income}</strong>
                  </div>
                  <div style={styles.badgeItem}>
                    <span>Applicant Category:</span>
                    <strong>{eligibilityContext.applicant_category}</strong>
                  </div>
                  <div style={styles.badgeItem}>
                    <span>Urban/Rural Status:</span>
                    <strong>{eligibilityContext.urban_rural.toUpperCase()}</strong>
                  </div>
                  <div style={styles.badgeItem}>
                    <span>Cultivable Land:</span>
                    <strong>{eligibilityContext.land_ownership_acres} Acres</strong>
                  </div>
                  <div style={styles.badgeItem}>
                    <span>Pucca House:</span>
                    <strong>{eligibilityContext.has_pucca_house ? "YES" : "NO"}</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Scheme Discovery & Optimization */}
        {activeTab === "discovery" && (
          <div style={styles.panelContent}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #f1f5f9", paddingBottom: "10px", marginBottom: "10px" }}>
              <h2 style={styles.sectionHeading}>Scheme Discovery & Benefit Optimization</h2>
            </div>
            <p style={styles.infoText}>
              Steps 5, 6, 9 & 10: RAG search across the 7 ingested policy documents in PostgreSQL. Checks eligibility rules, ranks schemes, and outputs expected benefits.
            </p>
            <div style={styles.formGroup}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <label style={styles.formLabel}>Describe the citizen query in natural language</label>
                <button
                  type="button"
                  onClick={() => setRawQuery(generateQueryFromProfile())}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#2563eb",
                    fontSize: "12px",
                    fontWeight: "600",
                    cursor: "pointer",
                    textDecoration: "underline",
                    padding: 0
                  }}
                >
                  🪄 Auto-Generate from Profile Details
                </button>
              </div>
              <textarea
                value={rawQuery}
                onChange={(e) => setRawQuery(e.target.value)}
                style={styles.formTextarea}
                rows={3}
              />
            </div>
            <button
              onClick={handleEntitlementCheck}
              disabled={checkLoading}
              style={styles.actionButton}
            >
              {checkLoading ? "Querying Postgres & Reasoning..." : "Discover & Optimize Schemes"}
            </button>
            {checkError && <div style={styles.errorAlert}>{checkError}</div>}
            
            {checkResult && (
              <div style={styles.resultContainer}>
                <div style={styles.summaryOverview}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <span style={{ fontSize: "14px", color: "#475569" }}>Overall Verdict:</span>
                    <strong style={{ fontSize: "16px", color: "#0f172a" }}>
                      {checkDetermination.citizen_verdict || "No schemes recommended"}
                    </strong>
                  </div>
                </div>

                {/* Differentiator: Benefit Optimization (Step 9) */}
                {checkDetermination.optimized_benefit_plan && checkDetermination.optimized_benefit_plan.length > 0 && (
                  <div style={styles.optimizedBlock}>
                    <h3 style={styles.subHeading}>✨ NemHem Benefit Optimizer Suggestion (Apply in this Order)</h3>
                    <p style={styles.infoText}>
                      We have ranked the schemes using operational factors: Benefit amount, approval probability, urgency, and document simplicity.
                    </p>
                    <div style={styles.optimizationList}>
                      {checkDetermination.optimized_benefit_plan.map((item) => (
                        <div key={item.scheme_name} style={styles.optimizerItem}>
                          <div style={styles.rankBadge}>#{item.rank}</div>
                          <div style={styles.optimizerDetails}>
                            <strong style={{ fontSize: "15px", color: "#0f172a" }}>{item.scheme_name}</strong>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", fontSize: "13px", color: "#475569", marginTop: "4px" }}>
                              <span>Benefit Value: <strong>{item.benefit_description}</strong></span>
                              <span>•</span>
                              <span>Profile Completeness: <strong>{item.readiness_score || 0}%</strong></span>
                            </div>
                            <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                              Status: <strong style={{
                                color: item.application_readiness === "READY" ? "#166534" : (item.application_readiness === "NOT_ELIGIBLE" ? "#991b1b" : "#b56902")
                              }}>
                                {item.application_readiness === "NEEDS_VERIFICATION" ? "Pending Verification" : 
                                 item.application_readiness === "MISSING_DOCUMENTS" ? "Missing Documents" : 
                                 item.application_readiness === "READY" ? "Ready" : "Not Eligible"}
                              </strong>
                              {item.missing_docs_count > 0 && ` | Missing: ${item.missing_docs_count} ${item.missing_docs_count === 1 ? 'document' : 'documents'}`}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Scheme Detail Breakdown */}
                <h3 style={styles.subHeading}>Matched Scheme Specifics</h3>
                <div style={styles.schemesGrid}>
                  {checkDetermination.schemes?.map((scheme) => {
                    const isExpanded = !!expandedSchemes[scheme.scheme_name];
                    return (
                      <div key={scheme.scheme_name} style={styles.schemeDetailCard}>
                        <div style={styles.schemeHeaderRow}>
                          <h4 style={styles.schemeTitle}>{scheme.scheme_name}</h4>
                          <span style={{
                            ...styles.verdictBadge,
                            background: scheme.application_readiness === "READY" ? "#e7f6ec" : (scheme.application_readiness === "NOT_ELIGIBLE" ? "#fdecea" : "#fff8e1"),
                            color: scheme.application_readiness === "READY" ? "#176b3a" : (scheme.application_readiness === "NOT_ELIGIBLE" ? "#b42318" : "#8a5a00")
                          }}>
                            {scheme.application_readiness === "NEEDS_VERIFICATION" ? "Needs Verification" : 
                             scheme.application_readiness === "MISSING_DOCUMENTS" ? "Missing Documents" : 
                             scheme.application_readiness === "READY" ? "Ready" : "Not Eligible"}
                          </span>
                        </div>
                        <p style={styles.schemeBenefitText}>Benefit Value: {scheme.benefit || "Varies"}</p>
                        
                        <div style={{ fontSize: "13px", color: "#475569", marginBottom: "10px", fontWeight: "600" }}>
                          ⚡ {scheme.scheme_name} Profile Completeness: {scheme.readiness_score || 0}%
                        </div>

                        {/* Explainable Eligibility Block */}
                        <div style={styles.explainableEligibilityBlock}>
                          {/* Status / Application Readiness */}
                          <div style={styles.explainableRow}>
                            <span style={styles.explainableLabel}>Status:</span>
                            <strong style={{
                              color: scheme.application_readiness === "READY" ? "#166534" : (scheme.application_readiness === "NOT_ELIGIBLE" ? "#991b1b" : "#b56902"),
                              fontSize: "13px"
                            }}>
                              {scheme.application_readiness === "NEEDS_VERIFICATION" ? "Pending Verification" : 
                               scheme.application_readiness === "MISSING_DOCUMENTS" ? "Missing Documents" : 
                               scheme.application_readiness === "READY" ? "Ready" : "Not Eligible"}
                            </strong>
                            {scheme.readiness_sublabel && (
                              <span style={{ fontSize: "12px", color: "#64748b", marginLeft: "4px" }}>
                                ({scheme.readiness_sublabel})
                              </span>
                            )}
                          </div>

                          {/* Matched Conditions */}
                          {scheme.met_criteria?.length > 0 && (
                            <div style={styles.explainableSection}>
                              <span style={styles.explainableLabel}>Matched Conditions:</span>
                              <div style={styles.explainableList}>
                                {scheme.met_criteria.map((c, i) => (
                                  <div key={i} style={styles.explainablePassItem}>
                                    ✓ {getFriendlyCondition(c)}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Needs Verification */}
                          {scheme.application_readiness !== "NOT_ELIGIBLE" && scheme.missing_information?.length > 0 && (
                            <div style={styles.explainableSection}>
                              <span style={styles.explainableLabel}>Needs Verification:</span>
                              <div style={styles.explainableList}>
                                {scheme.missing_information.map((f, i) => (
                                  <div key={i} style={{ color: "#334155", fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}>
                                    • {getFriendlyMissing(f)}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Missing Documents */}
                          {scheme.application_readiness !== "NOT_ELIGIBLE" && scheme.missing_documents?.length > 0 && (
                            <div style={styles.explainableSection}>
                              <span style={styles.explainableLabel}>Missing Documents:</span>
                              <div style={styles.explainableList}>
                                {scheme.missing_documents.map((docItem, i) => (
                                  <div key={i} style={{ color: "#334155", fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}>
                                    • {getFriendlyDocument(docItem.document)}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Next Steps */}
                          {scheme.application_readiness !== "NOT_ELIGIBLE" && scheme.next_steps?.length > 0 && (
                            <div style={styles.explainableSection}>
                              <span style={styles.explainableLabel}>Next Steps:</span>
                              <div style={styles.explainableList}>
                                {scheme.next_steps.map((step, i) => (
                                  <div key={i} style={{ color: "#334155", fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}>
                                    • {step}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Why This Recommendation? */}
                          {scheme.explanation?.reasoning && (
                            <div style={styles.explainableSection}>
                              <span style={styles.explainableLabel}>Why This Recommendation?</span>
                              <div style={styles.explainableWhyBox}>
                                {checkResult?.status === "GENERATING_EXPLANATION" && 
                                 checkResult?.determination?.optimized_benefit_plan?.slice(0, 3).some(item => item.scheme_name === scheme.scheme_name) && (
                                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#2563eb", fontWeight: "600", fontSize: "13px", marginBottom: "8px" }}>
                                    <span style={styles.pulseDotBlue}></span>
                                    <span>Generating detailed explanation...</span>
                                  </div>
                                )}
                                <div style={{ opacity: (checkResult?.status === "GENERATING_EXPLANATION" && checkResult?.determination?.optimized_benefit_plan?.slice(0, 3).some(item => item.scheme_name === scheme.scheme_name)) ? 0.6 : 1 }}>
                                  {scheme.explanation.reasoning}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Policy Citations & Reference Sources */}
                          {scheme.citations && scheme.citations.length > 0 && (
                            <div style={styles.explainableSection}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                                <span style={{...styles.explainableLabel, marginBottom: 0}}>Policy Citations & Reference Sources:</span>
                                {checkResult?.query_id && (
                                  <button
                                    onClick={() => handleOpenExplanation(checkResult.query_id)}
                                    style={{
                                      ...styles.actionButton,
                                      backgroundColor: checkResult.status !== "COMPLETED" ? "#f3f4f6" : "#f0f9ff",
                                      color: checkResult.status !== "COMPLETED" ? "#9ca3af" : "#0369a1",
                                      borderColor: checkResult.status !== "COMPLETED" ? "#e5e7eb" : "#bae6fd",
                                      cursor: checkResult.status !== "COMPLETED" ? "not-allowed" : "pointer"
                                    }}
                                  >
                                    {checkResult.status !== "COMPLETED" ? "⏳ Generating Audit Trail..." : "🕵️ Audit Trail & AI Reasoning"}
                                  </button>
                                )}
                              </div>
                              <div style={styles.citationsContainer}>
                                {scheme.citations.map((cit, idx) => (
                                  <div key={idx} style={styles.citationCard}>
                                    <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "4px" }}>
                                      <strong style={{ fontSize: "14px", color: "#1e293b" }}>{cit.file_name}</strong>
                                      <span style={{ fontSize: "12px", color: "#64748b" }}>Page {Array.isArray(cit.page_range) ? cit.page_range.join("-") : cit.page_range}</span>
                                    </div>
                                    {cit.excerpt && (
                                      <div style={{ fontSize: "13px", color: "#475569", lineHeight: "1.5" }}>
                                        {cit.excerpt}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Optional Advanced Details Accordion */}
                        <div style={{ marginTop: "14px", borderTop: "1px solid #e2e8f0", paddingTop: "12px" }}>
                          <button
                            type="button"
                            onClick={() => toggleSchemeDetails(scheme.scheme_name)}
                            style={{
                              background: "none",
                              border: "none",
                              color: "#2563eb",
                              fontSize: "13px",
                              fontWeight: "600",
                              cursor: "pointer",
                              padding: 0,
                              display: "flex",
                              alignItems: "center",
                              gap: "4px"
                            }}
                          >
                            {isExpanded ? "▼ Hide Evaluation Details" : "▶ View Evaluation Details"}
                          </button>
                          
                          {isExpanded && (
                            <div style={{ marginTop: "10px", padding: "12px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: "13px" }}>
                              {/* Matched Conditions */}
                              <div style={{ marginBottom: "10px" }}>
                                <strong style={{ display: "block", color: "#334155", marginBottom: "4px" }}>Matched Conditions:</strong>
                                {scheme.met_criteria?.length > 0 ? (
                                  <ul style={{ margin: 0, paddingLeft: "16px", color: "#475569" }}>
                                    {scheme.met_criteria.map((c, i) => <li key={i}>{getFriendlyCondition(c)}</li>)}
                                  </ul>
                                ) : <span style={{ color: "#94a3b8" }}>None</span>}
                              </div>
                              
                              {/* Failed Conditions */}
                              <div style={{ marginBottom: "10px" }}>
                                <strong style={{ display: "block", color: "#334155", marginBottom: "4px" }}>Failed Conditions:</strong>
                                {scheme.failed_conditions?.length > 0 ? (
                                  <ul style={{ margin: 0, paddingLeft: "16px", color: "#991b1b" }}>
                                    {scheme.failed_conditions.map((c, i) => <li key={i}>{getFriendlyCondition(c)}</li>)}
                                  </ul>
                                ) : <span style={{ color: "#94a3b8" }}>None</span>}
                              </div>

                              {/* Missing Information */}
                              <div style={{ marginBottom: "10px" }}>
                                <strong style={{ display: "block", color: "#334155", marginBottom: "4px" }}>Missing Information (Needs Verification):</strong>
                                {scheme.missing_information?.length > 0 ? (
                                  <ul style={{ margin: 0, paddingLeft: "16px", color: "#475569" }}>
                                    {scheme.missing_information.map((f, i) => <li key={i}>{getFriendlyMissing(f)}</li>)}
                                  </ul>
                                ) : <span style={{ color: "#94a3b8" }}>None</span>}
                              </div>

                              {/* Missing Documents */}
                              <div>
                                <strong style={{ display: "block", color: "#334155", marginBottom: "4px" }}>Missing Documents:</strong>
                                {scheme.missing_documents?.length > 0 ? (
                                  <ul style={{ margin: 0, paddingLeft: "16px", color: "#475569" }}>
                                    {scheme.missing_documents.map((docItem, i) => <li key={i}>{getFriendlyDocument(docItem.document)}</li>)}
                                  </ul>
                                ) : <span style={{ color: "#94a3b8" }}>None</span>}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Verification Agent (OCR Upload + Reconfirm) */}
        {activeTab === "verification" && (
          <div style={styles.panelContent}>
            <h2 style={styles.sectionHeading}>Verification Agent Integration</h2>
            <p style={styles.infoText}>
              Step 7: Upload simulated files. Our interoperable Verification Agent runs: Classification → OCR extraction → Field validation → Rules check → Profile cross-validation → Fraud/tampering analysis.
            </p>
            {!citizenId && <div style={styles.warningAlert}>A citizen must be registered first (Tab 1).</div>}
            
            {!verificationPipelineLogs ? (
              <>
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Select Document Type to verify</label>
                  <select
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                    style={styles.formSelect}
                  >
                    <option value="Aadhaar">Aadhaar Card</option>
                    <option value="Income Certificate">Income Certificate</option>
                    <option value="Caste/category certificate">Caste / Category Certificate</option>
                    <option value="Domicile Certificate">Domicile Residency Proof</option>
                    <option value="Disability Certificate">Disability Proof</option>
                  </select>
                </div>
                
                <div style={styles.formGroup}>
                  <label style={styles.formLabel}>Upload Document File</label>
                  <div style={styles.fileUploadWrapper}>
                    <input
                      type="file"
                      onChange={(e) => setFile(e.target.files[0])}
                      style={styles.fileInput}
                    />
                  </div>
                </div>

                <button
                  onClick={handleVerifyDocument}
                  disabled={verifyLoading || !citizenId}
                  style={{...styles.actionButton, marginTop: '8px'}}
                >
                  {verifyLoading ? "Scanning & Verifying Document..." : "Run Document Verification"}
                </button>
              </>
            ) : (
              <div style={styles.idCardContainer}>
                <div style={styles.idImagePanel}>
                  {file ? (
                    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 0, width: "100%" }}>
                      <img 
                        src={URL.createObjectURL(file)} 
                        alt="Uploaded Document" 
                        style={{ ...styles.idImage, width: "100%", height: "100%", objectFit: "contain" }} 
                      />
                    </div>
                  ) : (
                    <div style={{color: "#94a3b8", fontSize: "14px", flex: 1, display: "flex", alignItems: "center"}}>No image preview available</div>
                  )}
                  <div style={{marginTop: "16px", width: "100%", flexShrink: 0}}>
                    <div style={{
                      ...styles.verificationBadge, 
                      width: "100%", 
                      justifyContent: "center",
                      backgroundColor: verificationPipelineLogs.decision_result?.decision === "APPROVED" ? "#dcfce7" : (verificationPipelineLogs.decision_result?.decision === "REJECTED" ? "#fee2e2" : "#fef08a"),
                      color: verificationPipelineLogs.decision_result?.decision === "APPROVED" ? "#166534" : (verificationPipelineLogs.decision_result?.decision === "REJECTED" ? "#991b1b" : "#854d0e")
                    }}>
                      {verificationPipelineLogs.decision_result?.decision === "APPROVED" ? "✅ VERIFIED AUTHENTIC" : (verificationPipelineLogs.decision_result?.decision === "REJECTED" ? "❌ VERIFICATION FAILED" : "⚠️ MANUAL REVIEW")}
                    </div>
                  </div>
                </div>

                <div style={styles.idDetailsPanel}>
                  <div style={styles.idHeader}>
                    <h3 style={styles.idTitle}>{verificationPipelineLogs.document_type || "Unknown Document"}</h3>
                    <p style={styles.idSubtitle}>Confidence Score: {((verificationPipelineLogs.decision_result?.confidence || 0) * 100).toFixed(1)}% | Risk Level: {verificationPipelineLogs.fraud_result?.fraud_risk}</p>
                  </div>

                  <div style={styles.idFieldGrid}>
                    {Object.entries(verificationPipelineLogs.extracted_fields || {}).map(([key, value]) => (
                      <div key={key} style={styles.idField}>
                        <span style={styles.idFieldLabel}>{key.replace(/_/g, " ")}</span>
                        <span style={styles.idFieldValue}>{value?.toString() || "N/A"}</span>
                      </div>
                    ))}
                  </div>

                  {verificationPipelineLogs.decision_result?.decision !== "APPROVED" && verificationPipelineLogs.decision_result?.reasons && (
                    <div style={{
                      marginTop: "auto",
                      padding: "16px",
                      borderRadius: "8px",
                      backgroundColor: verificationPipelineLogs.decision_result?.decision === "REJECTED" ? "#fef2f2" : "#fefce8",
                      border: `1px solid ${verificationPipelineLogs.decision_result?.decision === "REJECTED" ? "#fecaca" : "#fef08a"}`,
                      color: verificationPipelineLogs.decision_result?.decision === "REJECTED" ? "#991b1b" : "#854d0e"
                    }}>
                      <h4 style={{ margin: "0 0 8px 0", fontSize: "14px", fontWeight: "700" }}>
                        {verificationPipelineLogs.decision_result?.decision === "REJECTED" ? "Reason for Failure:" : "Reason for Manual Review:"}
                      </h4>
                      <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" }}>
                        {verificationPipelineLogs.decision_result?.reasons?.map((reason, idx) => (
                          <li key={idx}>{reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div style={{...styles.idActions, marginTop: verificationPipelineLogs.decision_result?.decision !== "APPROVED" ? "16px" : "auto"}}>
                    <button 
                      onClick={() => {
                        setVerificationPipelineLogs(null);
                        setFile(null);
                      }} 
                      style={{...styles.secondaryButton, flex: 1}}
                    >
                      Scan Another Document
                    </button>
                    <button 
                      onClick={handleReconfirm} 
                      style={{...styles.actionButton, flex: 2, padding: "12px"}}
                    >
                      Process & Reconfirm Eligibility
                    </button>
                  </div>

                  {reconfirmResult && (
                    <div style={{...styles.reconfirmResultCard, marginTop: "16px"}}>
                      <div style={{fontSize: "14px", marginBottom: "8px"}}>Overall Decision Status: <strong style={{color: "#93c5fd"}}>{reconfirmResult.overall_decision}</strong></div>
                      <ul style={{margin: 0, paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "6px"}}>
                        {reconfirmResult.schemes?.map((s) => (
                          <li key={s.scheme_name}>
                            {s.scheme_name}: Preliminary verdict was <strong>{s.preliminary_verdict}</strong>, Document check: <strong>{s.verification_check}</strong>. Final Decision: <strong style={{color: s.final_decision === "ELIGIBLE" ? "#4ade80" : "#fca5a5"}}>{s.final_decision}</strong>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 5: Audit Compliance Logs (Step 14) */}
        {activeTab === "audit" && (
          <div style={styles.panelContent}>
            <h2 style={styles.sectionHeading}>Audit Agent: Decision Traceability</h2>
            <p style={styles.infoText}>
              Step 14: Traceability log entries kept by the independent compliance Audit Agent. Displays the exact reasons, rules applied, and documents used for each recommendation or rejection.
            </p>
            {!citizenId && <div style={styles.warningAlert}>A citizen must be registered first (Tab 1).</div>}
            
            {auditLoading ? (
              <div>Loading compliance records...</div>
            ) : auditLogs.length === 0 ? (
              <div style={styles.infoText}>No audit trace logs recorded for this citizen ID yet. Run a scheme check or submission first.</div>
            ) : (
              <div style={styles.auditLogsList}>
                {auditLogs.map((log) => (
                  <div key={log.id || log.audit_id || Math.random()} style={styles.auditLogCard}>
                    <div style={styles.auditHeader}>
                      <strong>Scheme: {log.policy_id || log.scheme_id || log.scheme_name}</strong>
                      <span style={{
                        ...styles.auditActionBadge,
                        backgroundColor: (log.status === "approved" || log.status === "RECOMMEND" || log.decision_result === "ELIGIBLE") ? "#e7f6ec" : ((log.status === "rejected" || log.status === "REJECT" || log.decision_result === "NOT_ELIGIBLE") ? "#fdecea" : "#fff8e1"),
                        color: (log.status === "approved" || log.status === "RECOMMEND" || log.decision_result === "ELIGIBLE") ? "#176b3a" : ((log.status === "rejected" || log.status === "REJECT" || log.decision_result === "NOT_ELIGIBLE") ? "#b42318" : "#8a5a00")
                      }}>{log.decision_result || log.status || log.action}</span>
                    </div>
                    <div style={styles.auditTime}>Logged on: {new Date(log.created_at || log.timestamp || Date.now()).toLocaleString()}</div>
                    
                    <div style={styles.auditDetailGrid}>
                      <div>
                        <strong>Verdict:</strong> <em>{log.decision_result || log.decision_trace?.verdict}</em>
                      </div>
                      <div>
                        <strong>Context ID:</strong> {log.context_id || log.decision_id || "N/A"}
                      </div>
                    </div>
                    
                    <div style={styles.auditJustify}>
                      <strong>Compliance Rule Results & Justification:</strong>
                      {log.rule_results && log.rule_results.length > 0 ? (
                        <ul style={{ margin: "8px 0 0 0", paddingLeft: "20px", fontSize: "13px", color: "#475569" }}>
                          {log.rule_results.map((rule, idx) => (
                            <li key={idx}>
                              {rule.rule_id}: <strong style={{color: rule.passed ? "#166534" : "#991b1b"}}>{rule.passed ? "PASSED" : "FAILED"}</strong>
                              {rule.evidence && <span style={{marginLeft: "6px"}}>- {rule.evidence}</span>}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p style={styles.excerptText}>{log.decision_trace?.reasons?.join(" ") || "No detailed rule trace available."}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      </main>

      {/* Explanation Modal */}
      {explanationModal.isOpen && (
        <div style={{
          position: "fixed",
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: "rgba(15, 23, 42, 0.6)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 1000,
          padding: "20px"
        }}>
          <div style={{
            background: "#fff",
            borderRadius: "12px",
            width: "100%",
            maxWidth: "700px",
            maxHeight: "90vh",
            overflowY: "auto",
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
          }}>
            <div style={{ padding: "20px", borderBottom: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, fontSize: "18px", color: "#0f172a" }}>AI Decision Reasoning & Audit Trace</h3>
              <button 
                onClick={() => setExplanationModal({ ...explanationModal, isOpen: false })}
                style={{ background: "none", border: "none", fontSize: "20px", cursor: "pointer", color: "#64748b" }}
              >
                ✕
              </button>
            </div>
            <div style={{ padding: "24px" }}>
              {explanationModal.loading ? (
                <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                  <div style={styles.pulseDotBlue}></div> Fetching cryptographic audit trace...
                </div>
              ) : explanationModal.error ? (
                <div style={styles.errorAlert}>Error loading explanation: {explanationModal.error}</div>
              ) : explanationModal.data ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                    <h4 style={{ margin: "0 0 12px 0", color: "#1e293b", fontSize: "16px", borderBottom: "1px solid #cbd5e1", paddingBottom: "8px" }}>
                      Decision Verdict: {explanationModal.data.verdict}
                    </h4>
                    
                    <div style={{ fontSize: "14px", color: "#334155", lineHeight: "1.6", whiteSpace: "pre-wrap" }}>
                      <strong>AI Reasoning:</strong>
                      <p>{explanationModal.data.reasons || explanationModal.data.ai_generated_response || "No advanced LLM explanation found for this decision."}</p>
                    </div>
                    
                    <div style={{ marginTop: "16px", display: "flex", flexWrap: "wrap", gap: "10px", fontSize: "13px" }}>
                      <div style={{ padding: "8px", background: "#fff", border: "1px solid #e2e8f0", borderRadius: "4px" }}>
                        <strong style={{ color: "#475569" }}>Policy Checked:</strong> {explanationModal.data.policy_used || "Unknown"}
                      </div>
                      <div style={{ padding: "8px", background: "#fff", border: "1px solid #e2e8f0", borderRadius: "4px" }}>
                        <strong style={{ color: "#475569" }}>Rules Version:</strong> {explanationModal.data.rules_applied || "v1"}
                      </div>
                      <div style={{ padding: "8px", background: "#fff", border: "1px solid #e2e8f0", borderRadius: "4px" }}>
                        <strong style={{ color: "#475569" }}>Confidence:</strong> {parseFloat(explanationModal.data.confidence_score || 0).toFixed(1)}%
                      </div>
                    </div>

                    {explanationModal.data.documents_used && explanationModal.data.documents_used.length > 0 && (
                      <div style={{ marginTop: "16px" }}>
                        <strong style={{ fontSize: "13px", color: "#475569" }}>Documents Referenced:</strong>
                        <ul style={{ margin: "8px 0 0 0", paddingLeft: "20px", fontSize: "13px", color: "#334155" }}>
                          {explanationModal.data.documents_used.map((d, i) => (
                            <li key={i}>{d}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {explanationModal.data.evidence_influencing_outcome && explanationModal.data.evidence_influencing_outcome.length > 0 && (
                      <div style={{ marginTop: "16px" }}>
                        <strong style={{ fontSize: "13px", color: "#475569" }}>Traceability Chain (Evidence):</strong>
                        <ul style={{ margin: "8px 0 0 0", paddingLeft: "20px", fontSize: "13px", color: "#334155" }}>
                          {explanationModal.data.evidence_influencing_outcome.map((ev, i) => (
                            <li key={i} style={{ marginBottom: "6px" }}>
                              <strong>{ev.rule_id}</strong>
                              <p style={{ margin: "2px 0 0 0", color: "#64748b" }}>Score: {ev.evidence_score} | Doc: {ev.document_type}</p>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    <div style={{ marginTop: "16px", fontSize: "11px", color: "#94a3b8" }}>
                      Decision ID: {explanationModal.data.decision_id}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// Inline Styled Objects with premium aesthetic (HSL palettes, clean typography layout)
const styles = {
  container: {
    maxWidth: "1140px",
    margin: "0 auto",
    padding: "24px",
    fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    color: "#334155"
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "2px solid #f1f5f9",
    paddingBottom: "18px",
    marginBottom: "24px"
  },
  headerTextGroup: {
    flex: 1
  },
  title: {
    margin: 0,
    fontSize: "26px",
    color: "#0f172a",
    fontWeight: 800
  },
  subtitle: {
    margin: "6px 0 0 0",
    color: "#64748b",
    fontSize: "14px",
    lineHeight: 1.5
  },
  activeCitizenChip: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    background: "#f0fdf4",
    border: "1px solid #bbf7d0",
    color: "#166534",
    padding: "8px 14px",
    borderRadius: "20px",
    fontSize: "13px"
  },
  pulseDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    backgroundColor: "#22c55e",
    boxShadow: "0 0 0 0 rgba(34, 197, 94, 0.7)",
    animation: "pulse 1.5s infinite"
  },
  pulseDotBlue: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    backgroundColor: "#2563eb",
    boxShadow: "0 0 0 0 rgba(37, 99, 235, 0.7)",
    animation: "pulse 1.5s infinite"
  },
  tabNav: {
    display: "flex",
    gap: "6px",
    marginBottom: "20px",
    overflowX: "auto",
    paddingBottom: "4px"
  },
  tabButton: {
    padding: "10px 16px",
    border: "1px solid #e2e8f0",
    background: "#f8fafc",
    color: "#64748b",
    fontSize: "13px",
    fontWeight: 600,
    borderRadius: "6px",
    cursor: "pointer",
    whiteSpace: "nowrap",
    transition: "all 0.2s ease"
  },
  tabButtonActive: {
    background: "#1e3a8a",
    color: "#fff",
    borderColor: "#1e3a8a"
  },
  panelCard: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "12px",
    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)",
    padding: "24px"
  },
  panelContent: {
    display: "flex",
    flexDirection: "column",
    gap: "18px"
  },
  sectionHeading: {
    margin: 0,
    fontSize: "18px",
    color: "#1e293b",
    fontWeight: 700
  },
  subHeading: {
    margin: "0 0 12px 0",
    fontSize: "15px",
    color: "#334155",
    fontWeight: 700,
    borderBottom: "1px solid #f1f5f9",
    paddingBottom: "6px"
  },
  cardHeading: {
    margin: "0 0 10px 0",
    fontSize: "14px",
    color: "#1e293b"
  },
  infoText: {
    margin: 0,
    color: "#64748b",
    fontSize: "13px",
    lineHeight: 1.5
  },
  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "6px"
  },
  formLabel: {
    fontSize: "12px",
    fontWeight: 700,
    color: "#475569"
  },
  formInput: {
    padding: "10px",
    border: "1px solid #cbd5e1",
    borderRadius: "6px",
    fontSize: "13px",
    transition: "all 0.2s",
    outline: "none"
  },
  formSelect: {
    padding: "10px",
    border: "1px solid #cbd5e1",
    borderRadius: "6px",
    fontSize: "13px",
    background: "#fff"
  },
  formTextarea: {
    padding: "10px",
    border: "1px solid #cbd5e1",
    borderRadius: "6px",
    fontSize: "13px",
    resize: "vertical"
  },
  checkboxContainer: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    margin: "8px 0"
  },
  checkboxLabel: {
    fontSize: "13px",
    color: "#334155",
    cursor: "pointer"
  },
  actionButton: {
    padding: "11px 20px",
    background: "#1e3a8a",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "13px",
    textAlign: "center"
  },
  secondaryButton: {
    padding: "9px 16px",
    background: "#f1f5f9",
    color: "#334155",
    border: "1px solid #cbd5e1",
    borderRadius: "6px",
    fontWeight: 600,
    cursor: "pointer",
    fontSize: "12px"
  },
  successAlert: {
    padding: "12px",
    borderRadius: "6px",
    background: "#f0fdf4",
    border: "1px solid #bbf7d0",
    color: "#166534",
    fontSize: "13px"
  },
  errorAlert: {
    padding: "12px",
    borderRadius: "6px",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    color: "#991b1b",
    fontSize: "13px"
  },
  warningAlert: {
    padding: "12px",
    borderRadius: "6px",
    background: "#fffbeb",
    border: "1px solid #fef3c7",
    color: "#92400e",
    fontSize: "13px"
  },
  guideToNext: {
    padding: "12px",
    borderRadius: "6px",
    background: "#eff6ff",
    border: "1px solid #bfdbfe",
    color: "#1e40af",
    fontSize: "13px"
  },
  splitGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "24px"
  },
  gridColumns3: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
    gap: "10px"
  },
  assessmentModelCard: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    marginTop: "10px"
  },
  badgeItem: {
    display: "flex",
    flexDirection: "column",
    padding: "6px 10px",
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "4px",
    fontSize: "12px"
  },
  resultContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "20px"
  },
  summaryOverview: {
    display: "flex",
    gap: "20px",
    background: "#eff6ff",
    border: "1px solid #dbeafe",
    padding: "14px 20px",
    borderRadius: "8px",
    fontSize: "14px"
  },
  statusGroup: {
    flex: 1
  },
  highlightText: {
    color: "#1e3a8a",
    marginLeft: "6px"
  },
  optimizedBlock: {
    background: "#faf5ff",
    border: "1px solid #f3e8ff",
    borderRadius: "8px",
    padding: "16px"
  },
  optimizationList: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    marginTop: "10px"
  },
  optimizerItem: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    background: "#fff",
    border: "1px solid #e9d5ff",
    borderRadius: "6px",
    padding: "8px 12px"
  },
  rankBadge: {
    background: "#c084fc",
    color: "#fff",
    fontWeight: 700,
    width: "28px",
    height: "28px",
    borderRadius: "50%",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontSize: "12px"
  },
  optimizerDetails: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    fontSize: "12px"
  },
  schemesGrid: {
    display: "flex",
    flexDirection: "column",
    gap: "14px"
  },
  schemeDetailCard: {
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    background: "#fff"
  },
  schemeHeaderRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "8px"
  },
  schemeTitle: {
    margin: 0,
    fontSize: "15px",
    color: "#0f172a"
  },
  verdictBadge: {
    padding: "4px 8px",
    borderRadius: "12px",
    fontSize: "11px",
    fontWeight: 700
  },
  schemeBenefitText: {
    margin: "0 0 8px 0",
    fontSize: "13px",
    fontWeight: 600,
    color: "#0f172a"
  },
  justificationText: {
    fontSize: "12px",
    color: "#334155",
    background: "#f8fafc",
    padding: "8px 12px",
    borderRadius: "4px",
    marginBottom: "10px"
  },
  bulletList: {
    fontSize: "12px",
    color: "#475569",
    marginBottom: "10px"
  },
  docsRequired: {
    fontSize: "12px",
    color: "#92400e",
    fontWeight: 600,
    marginBottom: "10px"
  },
  oldCitationsContainer: {
    borderTop: "1px solid #f1f5f9",
    paddingTop: "10px",
    fontSize: "11px"
  },
  citationExcerpt: {
    background: "#fdfdfd",
    border: "1px solid #f1f5f9",
    borderRadius: "4px",
    padding: "6px 10px",
    marginTop: "6px"
  },
  excerptText: {
    margin: "4px 0 0 0",
    fontStyle: "italic",
    color: "#475569"
  },
  pipelineLogBox: {
    background: "#1e293b",
    borderRadius: "8px",
    padding: "20px",
    color: "#f8fafc",
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },
  stepLogItem: {
    background: "#334155",
    borderRadius: "6px",
    padding: "10px 14px",
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    fontSize: "12px"
  },
  subtleText: {
    fontSize: "11px",
    color: "#cbd5e1",
    margin: 0
  },
  errorText: {
    color: "#f87171",
    fontSize: "12px"
  },
  reconfirmActionBlock: {
    borderTop: "1px solid #475569",
    paddingTop: "16px",
    marginTop: "8px",
    display: "flex",
    flexDirection: "column",
    gap: "10px"
  },
  reconfirmResultCard: {
    background: "#2a3b5c",
    padding: "12px",
    borderRadius: "6px",
    fontSize: "12px"
  },
  guidanceDataCard: {
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    background: "#f8fafc",
    marginTop: "12px",
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },
  preformatted: {
    margin: 0,
    fontSize: "11px",
    background: "#fff",
    border: "1px solid #e2e8f0",
    padding: "10px",
    borderRadius: "4px",
    overflowX: "auto"
  },
  affidavitBox: {
    background: "#fff7ed",
    border: "1px solid #ffedd5",
    color: "#c2410c",
    fontSize: "12px",
    padding: "12px",
    borderRadius: "4px",
    fontStyle: "italic",
    whiteSpace: "pre-line",
    lineHeight: 1.4
  },
  successText: {
    fontSize: "12px",
    color: "#166534",
    fontWeight: 600
  },
  submissionBlock: {
    borderTop: "1px solid #cbd5e1",
    paddingTop: "12px",
    display: "flex",
    flexDirection: "column",
    gap: "8px"
  },
  buttonGroup: {
    display: "flex",
    gap: "8px"
  },
  channelButton: {
    padding: "8px 12px",
    background: "#1e3a8a",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    fontSize: "11px",
    cursor: "pointer",
    fontWeight: 600
  },
  stepperContainer: {
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    background: "#f8fafc",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    fontSize: "12px"
  },
  remarksText: {
    color: "#475569"
  },
  stepperStages: {
    display: "flex",
    flexDirection: "column",
    gap: "14px",
    borderLeft: "2px solid #e2e8f0",
    paddingLeft: "16px",
    marginLeft: "8px"
  },
  stepStageItem: {
    position: "relative"
  },
  stepIndicatorDot: {
    position: "absolute",
    left: "-21px",
    top: "4px",
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    border: "2px solid #fff"
  },
  auditLogsList: {
    display: "flex",
    flexDirection: "column",
    gap: "14px"
  },
  auditLogCard: {
    border: "1px solid #cbd5e1",
    borderRadius: "8px",
    padding: "16px",
    background: "#fff"
  },
  auditHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center"
  },
  auditActionBadge: {
    padding: "4px 8px",
    borderRadius: "6px",
    fontSize: "11px",
    fontWeight: 700
  },
  auditTime: {
    fontSize: "11px",
    color: "#94a3b8",
    marginTop: "2px"
  },
  auditDetailGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "8px",
    fontSize: "12px",
    background: "#f8fafc",
    padding: "10px",
    borderRadius: "4px",
    margin: "10px 0"
  },
  fileUploadWrapper: {
    display: "flex",
    flexDirection: "column",
    gap: "8px"
  },
  fileInput: {
    padding: "10px",
    border: "1px dashed #cbd5e1",
    borderRadius: "8px",
    background: "#fff",
    cursor: "pointer",
    width: "100%",
    boxSizing: "border-box"
  },
  idCardContainer: {
    display: "flex",
    flexDirection: "row",
    gap: "32px",
    padding: "32px",
    background: "#ffffff",
    borderRadius: "16px",
    border: "1px solid #e2e8f0",
    boxShadow: "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05)",
    marginTop: "24px"
  },
  idImagePanel: {
    flex: "1",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    background: "#f8fafc",
    borderRadius: "12px",
    border: "1px dashed #cbd5e1",
    padding: "16px",
    minHeight: "250px"
  },
  idImage: {
    maxWidth: "100%",
    maxHeight: "350px",
    objectFit: "contain",
    borderRadius: "8px",
    boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)"
  },
  idDetailsPanel: {
    flex: "2",
    display: "flex",
    flexDirection: "column",
    gap: "20px"
  },
  idHeader: {
    borderBottom: "2px solid #e2e8f0",
    paddingBottom: "16px",
    marginBottom: "4px"
  },
  idTitle: {
    fontSize: "24px",
    fontWeight: "700",
    color: "#0f172a",
    margin: "0 0 8px 0"
  },
  idSubtitle: {
    fontSize: "14px",
    color: "#64748b",
    margin: "0",
    fontWeight: "500"
  },
  idFieldGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "20px"
  },
  idField: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    background: "#f8fafc",
    padding: "12px 16px",
    borderRadius: "8px",
    border: "1px solid #f1f5f9"
  },
  idFieldLabel: {
    fontSize: "12px",
    fontWeight: "600",
    color: "#64748b",
    textTransform: "uppercase",
    letterSpacing: "0.5px"
  },
  idFieldValue: {
    fontSize: "16px",
    fontWeight: "600",
    color: "#0f172a"
  },
  verificationBadge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "8px 16px",
    borderRadius: "8px",
    fontSize: "14px",
    fontWeight: "700",
    gap: "8px",
    boxSizing: "border-box"
  },
  idActions: {
    marginTop: "auto",
    display: "flex",
    gap: "16px",
    borderTop: "1px solid #e2e8f0",
    paddingTop: "24px"
  },
  auditJustify: {
    fontSize: "12px",
    color: "#334155"
  },
  explainableEligibilityBlock: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    marginTop: "12px",
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },
  explainableRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "13px"
  },
  explainableLabel: {
    fontWeight: 700,
    fontSize: "12px",
    color: "#475569",
    textTransform: "uppercase",
    letterSpacing: "0.5px"
  },
  explainableSection: {
    display: "flex",
    flexDirection: "column",
    gap: "6px"
  },
  explainableList: {
    display: "flex",
    flexDirection: "column",
    gap: "4px"
  },
  explainablePassItem: {
    color: "#166534",
    fontWeight: "600",
    fontSize: "13px",
    display: "flex",
    alignItems: "center",
    gap: "6px"
  },
  explainableFailItem: {
    color: "#991b1b",
    fontWeight: "600",
    fontSize: "13px",
    display: "flex",
    alignItems: "center",
    gap: "6px"
  },
  explainableDocItem: {
    color: "#475569",
    fontSize: "13px",
    paddingLeft: "8px"
  },
  explainableWhyBox: {
    fontSize: "13px",
    color: "#334155",
    background: "#fff7ed",
    border: "1px solid #ffedd5",
    padding: "10px 12px",
    borderRadius: "6px",
    fontStyle: "italic",
    lineHeight: 1.4
  },
  citationsContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    marginTop: "4px"
  },
  citationCard: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    display: "flex",
    flexDirection: "column",
    gap: "6px"
  }
};

export default EntitlementDashboard;
