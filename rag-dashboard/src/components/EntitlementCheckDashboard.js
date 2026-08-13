import React, { useState, useEffect } from "react";
import axios from "axios";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const EntitlementCheckDashboard = () => {
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchAuditLogs = async () => {
    try {
      const timestamp = new Date().getTime();
      const response = await axios.get(`${API_URL}/api/v1/gaca/decisions/all?_t=${timestamp}`);
      setAuditLogs(Array.isArray(response.data) ? response.data : []);
      setError("");
    } catch (err) {
      console.error("Failed to fetch audit logs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
    const interval = setInterval(fetchAuditLogs, 10000); // update similar to query/grievances
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>Loading Audit Logs...</div>;

  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <h2 style={styles.title}>Audit & Compliance Dashboard (Entitlement Checks)</h2>
        <span style={styles.badgeCount}>{auditLogs.length} Records</span>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.auditLogsList}>
        {auditLogs.length === 0 ? (
          <div style={styles.emptyState}>No audit trace logs recorded yet.</div>
        ) : (
          auditLogs.map((log) => {
            let badgeBg = "#fee2e2";
            let badgeColor = "#991b1b";
            if (["PASSED", "APPROVED", "ELIGIBLE", "APPLICATION_SUBMITTED"].includes(log.decision_result)) {
              badgeBg = "#dcfce7";
              badgeColor = "#166534";
            } else if (["PENDING_DOCS", "PENDING"].includes(log.decision_result)) {
              badgeBg = "#fef08a";
              badgeColor = "#854d0e";
            }
            
            const conf = log.confidence_score > 1 ? log.confidence_score : log.confidence_score * 100;

            return (
            <div key={log.decision_id} style={styles.auditLogCard}>
              <div style={styles.auditHeader}>
                <span style={styles.auditAgentName}>Agent: {log.responsible_agent}</span>
                <span
                  style={{
                    ...styles.auditActionBadge,
                    backgroundColor: badgeBg,
                    color: badgeColor,
                  }}
                >
                  Decision: {log.decision_result}
                </span>
              </div>
              <div style={styles.auditTime}>Logged on: {new Date(log.timestamp).toLocaleString()}</div>

              <div style={styles.auditDetailGrid}>
                <div style={styles.auditDetailItem}>
                  <span style={styles.auditDetailLabel}>Decision Type</span>
                  <span style={styles.auditDetailValue}>{log.decision_type || "N/A"}</span>
                </div>
                <div style={styles.auditDetailItem}>
                  <span style={styles.auditDetailLabel}>Scheme / App ID</span>
                  <span style={styles.auditDetailValue}>{log.scheme_id || log.application_id || "N/A"}</span>
                </div>
                <div style={styles.auditDetailItem}>
                  <span style={styles.auditDetailLabel}>Confidence</span>
                  <span style={styles.auditDetailValue}>{Math.min(conf, 100).toFixed(1)}%</span>
                </div>
                <div style={styles.auditDetailItem}>
                  <span style={styles.auditDetailLabel}>Policy Applied</span>
                  <span style={styles.auditDetailValue}>{log.policy_id || "N/A"}</span>
                </div>
              </div>

              <div style={styles.auditJustify}>
                <strong>Traceability Justification:</strong>
                {log.decision_trace?.reasoning ? (
                  <p style={{ margin: "4px 0 0 0", color: "#334155" }}>{log.decision_trace.reasoning}</p>
                ) : log.decision_trace?.documents_attached ? (
                  <div style={{ marginTop: "4px" }}>
                    <p style={{ margin: "0 0 8px 0", color: "#334155" }}>
                      {log.decision_trace.message || "Documents submitted successfully."}
                    </p>
                    <strong style={{ color: "#334155" }}>Documents verified and submitted:</strong>
                    <ul style={{ margin: "4px 0 0 0", paddingLeft: "20px", color: "#334155" }}>
                      {log.decision_trace.documents_attached.map((doc, idx) => (
                        <li key={idx}>{doc}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <ul style={{ margin: "4px 0 0 0", paddingLeft: "20px", color: "#334155" }}>
                    {log.rule_results?.map((rule, idx) => (
                      <li key={idx}>
                        {rule.rule}: {rule.passed ? "✅ Passed" : "❌ Failed"} - {rule.reason}
                      </li>
                    ))}
                    {(!log.rule_results || log.rule_results.length === 0) && (
                      <li>Automatic verification completed based on citizen profile attributes.</li>
                    )}
                  </ul>
                )}
              </div>
            </div>
            );
          })
        )}
      </div>
    </div>
  );
};

const styles = {
  container: {
    padding: "20px 0",
    fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "24px",
    borderBottom: "2px solid #003366",
    paddingBottom: "12px",
  },
  title: {
    margin: 0,
    color: "#003366", // Navy Blue
    fontWeight: "600",
    fontSize: "24px",
  },
  badgeCount: {
    backgroundColor: "#003366",
    color: "#fff",
    padding: "4px 12px",
    borderRadius: "16px",
    fontSize: "14px",
    fontWeight: "bold",
  },
  auditLogsList: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  auditLogCard: {
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    backgroundColor: "#fff",
    borderLeft: "4px solid #3b82f6",
    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
  },
  auditHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "4px",
  },
  auditAgentName: {
    fontWeight: "600",
    fontSize: "14px",
    color: "#1e293b",
  },
  auditActionBadge: {
    fontSize: "12px",
    fontWeight: "600",
    padding: "4px 8px",
    borderRadius: "4px",
  },
  auditTime: {
    fontSize: "12px",
    color: "#64748b",
    marginBottom: "12px",
  },
  auditDetailGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "12px",
    backgroundColor: "#f8fafc",
    padding: "12px",
    borderRadius: "6px",
    marginBottom: "12px",
  },
  auditDetailItem: {
    display: "flex",
    flexDirection: "column",
  },
  auditDetailLabel: {
    fontSize: "11px",
    textTransform: "uppercase",
    color: "#94a3b8",
    fontWeight: "600",
    marginBottom: "2px",
  },
  auditDetailValue: {
    fontSize: "13px",
    color: "#0f172a",
    fontWeight: "500",
  },
  auditJustify: {
    fontSize: "13px",
    backgroundColor: "#fefced",
    border: "1px solid #fef08a",
    padding: "12px",
    borderRadius: "6px",
    color: "#b45309",
  },
  emptyState: {
    textAlign: "center",
    padding: "60px 20px",
    backgroundColor: "#f8fafc",
    borderRadius: "8px",
    color: "#64748b",
    fontSize: "16px",
    border: "2px dashed #cbd5e1",
  },
  error: {
    backgroundColor: "#fee2e2",
    color: "#b91c1c",
    padding: "12px",
    borderRadius: "6px",
    marginBottom: "20px",
  },
};

export default EntitlementCheckDashboard;
