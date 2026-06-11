/** rag-dashboard/src/App.js */

import React, { useState, useEffect } from "react";
import UploadForm from "./components/UploadForm";
import JobDashboard from "./components/JobDashboard";
import QueryDashboard from "./components/QueryDashboard";

// ✅ EXISTING
import BulkIngestionDashboard from "./components/BulkIngestionDashboard";

// 🔐 NEW AUTH COMPONENTS
import Login from "./components/auth/Login";
import Signup from "./components/auth/Signup";

// 🏛️ NEW DAY 5 DASHBOARD
import GrievanceDashboard from "./components/GrievanceDashboard";
import SubmitGrievance from "./components/SubmitGrievance";

// 🔍 NEW VERIFICATION DASHBOARD
import VerificationDashboard from "./components/VerificationDashboard";

/**
 * App Component
 * ----------------------------------------
 * Responsibilities:
 * - Authentication gate (NEW)
 * - Hold current jobId (from upload)
 * - Toggle between ingestion / bulk / query dashboards
 */
function App() {
  const [jobId, setJobId] = useState(null);

  // 🔥 View control (UNCHANGED)
  const [view, setView] = useState("single");

  // ============================================================
  // 🔐 AUTH STATE (NEW)
  // ============================================================
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const [authView, setAuthView] = useState("login"); // login | signup

  useEffect(() => {
    const token = localStorage.getItem("token");

    setIsAuthenticated(!!token);
  }, []);

  /**
   * Reset frontend dashboard state
   */
  const handleReset = () => {
    setJobId(null);
  };

  // ============================================================
  // 🔐 AUTH GATE (CRITICAL)
  // ============================================================
  if (!isAuthenticated) {
    return (
      <div style={styles.authPage}>
        
        {authView === "login" ? (
          <>
            <Login
              onLogin={() => {
                setIsAuthenticated(true);
              }}
            />

            <p style={styles.switchText}>
              Don't have an account?{" "}
              <span onClick={() => setAuthView("signup")} style={styles.link}>
                Signup
              </span>
            </p>
          </>
        ) : (
          <>
            <Signup />

            <p style={styles.switchText}>
              Already have an account?{" "}
              <span onClick={() => setAuthView("login")} style={styles.link}>
                Login
              </span>
            </p>
          </>
        )}

      </div>
    );
  }

  // ============================================================
  // 🔓 MAIN APP (UNCHANGED LOGIC)
  // ============================================================
  return (
    <div style={styles.page}>
      
      {/* ================= HEADER ================= */}
      <div style={styles.header}>
        <h1 style={styles.title}>📄 Government RAG Ingestion</h1>
        <p style={styles.subtitle}>
          Upload and process structured government documents
        </p>

        {/* 🔐 LOGOUT BUTTON (NEW) */}
        <button
          onClick={() => {
            localStorage.removeItem("token");
            localStorage.removeItem("role");

            setIsAuthenticated(false);

            // 🔥 ensures full reset
            window.location.reload();
          }}
          style={styles.logoutButton}
        >
          Logout
        </button>

        {/* RESET BUTTON */}
        <button onClick={handleReset} style={styles.resetButton}>
          Reset Dashboard
        </button>

        {/* 🚀 BULK INGESTION BUTTON */}
        <button 
          onClick={() => setView("bulk")} 
          style={styles.bulkButton}
        >
          Bulk Ingestion
        </button>

        {/* 🏛️ GRIEVANCE OFFICER BUTTON */}
        <button 
          onClick={() => setView("grievance")} 
          style={styles.grievanceButton}
        >
          Grievance Officer
        </button>

        {/* 🙋 CITIZEN GRIEVANCE PORTAL BUTTON */}
        <button 
          onClick={() => setView("submit_grievance")} 
          style={styles.citizenButton}
        >
          Citizen Portal
        </button>

        {/* 🔍 QUERY DASHBOARD BUTTON */}
        <button 
          onClick={() => setView("query")} 
          style={styles.queryButton}
        >
          Query Dashboard
        </button>

        {/* 📋 VERIFICATION AGENT BUTTON */}
        <button 
          onClick={() => setView("verification")} 
          style={styles.verificationButton}
        >
          Verification Agent
        </button>
      </div>

      {/* ================= MAIN CONTENT ================= */}

      {view === "single" ? (
        <div style={styles.grid}>
          
          <div style={styles.card}>
            <UploadForm setJobId={setJobId} />
          </div>

          <div style={styles.card}>
            <JobDashboard 
              currentJobId={jobId} 
              resetTrigger={jobId === null} 
            />
          </div>

        </div>

      ) : view === "bulk" ? (

        <div style={styles.card}>
          <BulkIngestionDashboard 
            goBack={() => setView("single")} 
          />
        </div>

      ) : view === "grievance" ? (

        <GrievanceDashboard />

      ) : view === "submit_grievance" ? (

        <SubmitGrievance />

      ) : view === "verification" ? (

        <VerificationDashboard />

      ) : (

        <div style={styles.card}>
          <QueryDashboard />
        </div>

      )}
    </div>
  );
}

/**
 * ================= STYLES =================
 */
const styles = {
  page: {
    padding: "30px",
    fontFamily: "Segoe UI, sans-serif",
    background: "#f5f7fb",
    minHeight: "100vh"
  },

  // 🔐 AUTH PAGE STYLE
  authPage: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "100vh",
    background: "#f5f7fb"
  },

  switchText: {
    marginTop: "10px",
    color: "#555"
  },

  link: {
    color: "#007bff",
    cursor: "pointer",
    fontWeight: "bold"
  },

  header: {
    marginBottom: "30px"
  },

  title: {
    margin: 0
  },

  subtitle: {
    color: "#666"
  },

  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
    gap: "20px"
  },

  card: {
    background: "#fff",
    padding: "20px",
    borderRadius: "12px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.08)"
  },

  resetButton: {
    marginTop: "10px",
    padding: "8px 16px",
    background: "#ff4d4f",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer"
  },

  bulkButton: {
    marginTop: "10px",
    marginLeft: "10px",
    padding: "8px 16px",
    background: "#6f42c1",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer"
  },

  grievanceButton: {
    marginTop: "10px",
    marginLeft: "10px",
    padding: "8px 16px",
    background: "#003366", // Navy Blue
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer"
  },

  citizenButton: {
    marginTop: "10px",
    marginLeft: "10px",
    padding: "8px 16px",
    background: "#28a745", // Green
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer"
  },

  queryButton: {
    marginTop: "10px",
    marginLeft: "10px",
    padding: "8px 16px",
    background: "#17a2b8",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer"
  },

  verificationButton: {
    marginTop: "10px",
    marginLeft: "10px",
    padding: "8px 16px",
    background: "#fd7e14", // Orange
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer"
  },

  // 🔐 NEW
  logoutButton: {
    marginTop: "10px",
    marginRight: "10px",
    padding: "8px 16px",
    background: "#343a40",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer"
  }
};

export default App;