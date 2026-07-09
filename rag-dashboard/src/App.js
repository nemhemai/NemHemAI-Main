/** rag-dashboard/src/App.js */

import React, { useState, useEffect } from "react";
import logo from "./assets/nemhem-logo.svg";
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

// 🏛️ NEW ENTITLEMENT & VERIFICATION DASHBOARD
import EntitlementDashboard from "./components/EntitlementDashboard";

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
    if (authView === "login") {
      return (
        <Login
          onLogin={() => setIsAuthenticated(true)}
          onSwitchSignup={() => setAuthView("signup")}
        />
      );
    } else {
      return (
        <Signup
          onSwitchLogin={() => setAuthView("login")}
        />
      );
    }
  }

  const getNavBtnStyle = (btnView) => {
    if (view !== btnView) return styles.navBtn;
    
    const base = {
      padding: "8px 16px",
      border: "none",
      borderRadius: "8px",
      fontSize: "14px",
      fontWeight: "600",
      cursor: "pointer",
      transition: "all 0.2s ease"
    };

    switch(btnView) {
      case "single": return { ...base, background: "#eff6ff", color: "#1d4ed8" }; // Blue
      case "bulk": return { ...base, background: "#f3e8ff", color: "#7e22ce" }; // Purple
      case "query": return { ...base, background: "#ecfdf5", color: "#047857" }; // Emerald
      case "grievance": return { ...base, background: "#fff7ed", color: "#c2410c" }; // Orange
      case "entitlement": return { ...base, background: "#f0fdfa", color: "#0f766e" }; // Teal
      default: return { ...base, background: "#f1f5f9", color: "#0f172a" };
    }
  };

  // ============================================================
  // 🔓 MAIN APP (UNCHANGED LOGIC)
  // ============================================================
  return (
    <div style={styles.page}>
      
      {/* ================= NAVBAR ================= */}
      <div style={styles.navbar}>
        <div style={styles.headerBrand}>
          <img src={logo} alt="NemhemAI Logo" style={styles.logoSmall} />
          <h1 style={styles.title}>NemhemAI</h1>
          <span style={styles.badge}>Gov RAG</span>
        </div>

        <div style={styles.navActions}>
          <button onClick={() => setView("single")} style={getNavBtnStyle("single")}>Single Upload</button>
          <button onClick={() => setView("bulk")} style={getNavBtnStyle("bulk")}>Bulk Upload</button>
          <button onClick={() => setView("query")} style={getNavBtnStyle("query")}>Query</button>
          <button onClick={() => setView("grievance")} style={getNavBtnStyle("grievance")}>Grievance Officer</button>
          <button onClick={() => setView("entitlement")} style={getNavBtnStyle("entitlement")}>Entitlement Agent</button>
          
          <div style={styles.navDivider}></div>
          
          <button onClick={handleReset} style={styles.dangerBtn}>Reset</button>
          <button onClick={() => {
            localStorage.removeItem("token");
            localStorage.removeItem("role");
            setIsAuthenticated(false);
            window.location.reload();
          }} style={styles.logoutBtn}>Logout</button>
        </div>
      </div>

      {/* ================= MAIN CONTENT ================= */}
      <div style={styles.mainContent}>

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

      ) : view === "entitlement" ? (

        <EntitlementDashboard />

      ) : (

        <div style={styles.card}>
          <QueryDashboard />
        </div>

      )}
      </div>
    </div>
  );
}

/**
 * ================= STYLES =================
 */
const styles = {
  page: {
    fontFamily: "'Inter', 'Segoe UI', sans-serif",
    background: "#f4f7fb",
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column"
  },

  navbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    background: "#ffffff",
    padding: "0 32px",
    height: "72px",
    borderBottom: "1px solid #e2e8f0",
    boxShadow: "0 1px 3px rgba(0,0,0,0.04)"
  },

  headerBrand: {
    display: "flex",
    alignItems: "center",
    gap: "12px"
  },

  logoSmall: {
    width: "36px",
    height: "36px",
    filter: "drop-shadow(0px 2px 4px rgba(0,0,0,0.1))"
  },

  title: {
    margin: 0,
    color: "#001f3f",
    fontSize: "24px",
    fontWeight: "700",
    letterSpacing: "0.5px"
  },

  badge: {
    background: "#e0e7ff",
    color: "#3730a3",
    padding: "4px 8px",
    borderRadius: "6px",
    fontSize: "12px",
    fontWeight: "600",
    marginLeft: "8px"
  },

  navActions: {
    display: "flex",
    alignItems: "center",
    gap: "8px"
  },

  navBtn: {
    padding: "8px 16px",
    background: "transparent",
    color: "#475569",
    border: "none",
    borderRadius: "8px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.2s ease"
  },

  navDivider: {
    width: "1px",
    height: "24px",
    background: "#cbd5e1",
    margin: "0 8px"
  },

  dangerBtn: {
    padding: "8px 16px",
    background: "#fee2e2",
    color: "#b91c1c",
    border: "none",
    borderRadius: "8px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.2s ease"
  },

  logoutBtn: {
    padding: "8px 16px",
    background: "#1e293b",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.2s ease"
  },

  mainContent: {
    padding: "32px",
    flex: 1
  },

  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(480px, 1fr))",
    gap: "24px"
  },

  card: {
    background: "#fff",
    padding: "32px",
    borderRadius: "16px",
    boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)",
    border: "1px solid #e2e8f0"
  }
};

export default App;