import React, { useState, useEffect } from "react";
import axios from "axios";
import ReactMarkdown from 'react-markdown';

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const GrievanceDashboard = () => {
  const [grievances, setGrievances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editedResponses, setEditedResponses] = useState({});
  const [activeDocsGrievance, setActiveDocsGrievance] = useState(null);
  const [activeImageGrievance, setActiveImageGrievance] = useState(null);
  const [briefingNote, setBriefingNote] = useState(null);
  const [briefingLoading, setBriefingLoading] = useState(false);

  const fetchGrievances = async () => {
    try {
      // Use auth token if the rest of the app requires it
      const token = localStorage.getItem("token");
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      
      const response = await axios.get(`${API_URL}/api/v1/grievances/`, { headers });
      setGrievances(response.data);
      setError("");
    } catch (err) {
      console.error("Failed to fetch grievances", err);
      // Fallback or ignore if it's just a polling error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGrievances();
    // Poll every 10 seconds for new grievances
    const interval = setInterval(fetchGrievances, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Initialize edited responses with official response (if already approved) or AI draft
    setEditedResponses((prev) => {
      const newEdited = { ...prev };
      grievances.forEach((g) => {
        if (!newEdited[g.id] && (g.official_response || g.ai_draft_response)) {
          newEdited[g.id] = g.official_response || g.ai_draft_response || "";
        }
      });
      return newEdited;
    });
  }, [grievances]);

  const handleApprove = async (id) => {
    try {
      const finalResponse = editedResponses[id] || "";
      const token = localStorage.getItem("token");
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.put(`${API_URL}/api/v1/grievances/${id}/approve`, { official_response: finalResponse }, { headers });
      
      // Update local state to show approved immediately
      setGrievances(prev => prev.map(g => 
        g.id === id ? { ...g, status: "APPROVED", official_response: finalResponse } : g
      ));
    } catch (err) {
      alert("Failed to approve grievance. See console for details.");
      console.error(err);
    }
  };

  const handleGenerateBriefing = async (grievance) => {
    setBriefingLoading(true);
    setBriefingNote(null);
    try {
      const token = localStorage.getItem("token");
      const headers = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      
      const payload = {
        query: `Briefing for grievance: ${grievance.category} - ${grievance.description || "No description"}`,
        context_texts: grievance.retrieved_context ? grievance.retrieved_context.map(c => typeof c === 'string' ? c : c.text) : [],
        role: "field_officer"
      };

      const response = await fetch(`${API_URL}/api/v1/briefings/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setBriefingLoading(false); // Stop loading once stream starts
      setBriefingNote(""); // Initialize as string

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          setBriefingNote(prev => (prev || "") + chunk);
        }
      }
    } catch (err) {
      console.error("Briefing generation failed:", err);
      alert("Failed to generate briefing.");
      setBriefingLoading(false);
    }
  };

  // Color mappings for badges
  const getSeverityColor = (score) => {
    if (!score) return "#6c757d";
    if (score >= 8) return "#dc3545"; // Red for high severity
    if (score >= 5) return "#fd7e14"; // Orange for medium
    if (score >= 3) return "#ffc107"; // Yellow
    return "#28a745"; // Green for low severity
  };

  const getToneColor = (tone) => {
    switch (tone) {
      case "ANGRY": return "#dc3545";
      case "DISTRESSED": return "#fd7e14";
      case "NEUTRAL": return "#17a2b8";
      case "POLITE": return "#28a745";
      default: return "#6c757d";
    }
  };

  const getUrgencyColor = (urgency) => {
    switch (urgency?.toUpperCase()) {
      case "HIGH": return "#dc3545"; // Red
      case "MEDIUM": return "#fd7e14"; // Orange
      case "LOW": return "#28a745"; // Green
      default: return "#6c757d"; // Gray
    }
  };

  if (loading) return <div style={styles.loading}>Loading Grievances...</div>;

  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <h2 style={styles.title}>Grievance Officer Dashboard</h2>
        <span style={styles.badgeCount}>{grievances.length} Active Tickets</span>
      </div>
      
      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.grid}>
        {grievances.map((g) => (
          <div key={g.id} style={styles.card}>
            
            {/* Header Section */}
            <div style={styles.cardHeader}>
              <div>
                <h3 style={styles.category}>{g.category}</h3>
                <p style={styles.date}>
                  {new Date(g.created_at).toLocaleString()} • Citizen ID: {g.citizen_id.slice(0, 8)}...
                </p>
              </div>
              <div style={styles.badgeContainer}>
                {g.urgency && (
                  <span style={{ ...styles.badge, backgroundColor: getUrgencyColor(g.urgency), color: '#fff' }}>
                    {g.urgency?.toUpperCase() === 'HIGH' ? '🔴 Critical' : 
                     g.urgency?.toUpperCase() === 'MEDIUM' ? '🟠 Moderate' : 
                     g.urgency?.toUpperCase() === 'LOW' ? '🟢 Routine' : g.urgency}
                  </span>
                )}
                {g.severity_score && (
                  <span style={{ ...styles.badge, backgroundColor: getSeverityColor(g.severity_score), color: '#fff' }}>
                    Severity: {g.severity_score}/10
                  </span>
                )}
                {g.tone && (
                  <span style={{ ...styles.badge, backgroundColor: getToneColor(g.tone), color: '#fff' }}>
                    {g.tone}
                  </span>
                )}
              </div>
            </div>

            <div style={styles.cardBody}>
              {/* Left Column: Citizen Complaint */}
              <div style={styles.contentColumn}>
                <div style={styles.contentSection}>
                  <h4 style={styles.sectionTitle}>Citizen Complaint:</h4>
                  <p style={{...styles.description, whiteSpace: 'pre-wrap'}}>
                    {g.description ? `"${g.description}"` : (g.has_image ? "[Image-only complaint. See attached picture.]" : "[No description provided]")}
                  </p>
                  
                  {g.has_image && (
                    <button 
                      style={styles.imageButton}
                      onClick={() => setActiveImageGrievance(g)}
                    >
                      🖼️ View Attached Picture
                    </button>
                  )}
                </div>
              </div>

              {/* Right Column: AI Draft and Action */}
              <div style={styles.responseColumn}>
                <div style={styles.contentSection}>
                  <div style={styles.draftHeaderRow}>
                    <h4 style={{ ...styles.sectionTitle, margin: 0 }}>Draft / Official Response:</h4>
                    {g.retrieved_context && g.retrieved_context.length > 0 && (
                      <button 
                        style={styles.referredLink}
                        onClick={() => setActiveDocsGrievance(g)}
                      >
                        📄 View Referred Docs
                      </button>
                    )}
                  </div>
                  <div style={styles.aiDraft}>
                    {g.status === 'APPROVED' ? (
                      <p style={{ margin: 0 }}>{g.official_response}</p>
                    ) : g.ai_draft_response ? (
                      <textarea
                        style={styles.responseEditor}
                        value={editedResponses[g.id] !== undefined ? editedResponses[g.id] : g.ai_draft_response}
                        onChange={(e) => setEditedResponses({ ...editedResponses, [g.id]: e.target.value })}
                      />
                    ) : (
                      <p style={styles.draftPending}>Generative AI is drafting response...</p>
                    )}
                  </div>
                </div>

                {/* Action Section */}
                <div style={styles.actionSection}>
                  <div style={styles.actionButtons}>
                    <button 
                      style={{
                        ...styles.approveButton,
                        opacity: g.status === 'APPROVED' || !g.ai_draft_response ? 0.5 : 1,
                        cursor: g.status === 'APPROVED' || !g.ai_draft_response ? 'not-allowed' : 'pointer'
                      }}
                      disabled={g.status === 'APPROVED' || !g.ai_draft_response}
                      onClick={() => handleApprove(g.id)}
                    >
                      {g.status === 'APPROVED' ? 'Approved ✓' : 'Approve Response'}
                    </button>
                  </div>
                  <span style={{ 
                    ...styles.statusText, 
                    color: g.status === 'APPROVED' ? '#28a745' : '#6c757d' 
                  }}>
                    Status: {g.status}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
        {grievances.length === 0 && (
          <div style={styles.emptyState}>No grievances found. The queue is clear.</div>
        )}
      </div>

      {/* Slidebar for Referred Documents */}
      {activeDocsGrievance && (
        <div style={styles.slidebarOverlay} onClick={() => setActiveDocsGrievance(null)}>
          <div style={{...styles.slidebar, width: '600px'}} onClick={(e) => e.stopPropagation()}>
            <div style={styles.slidebarHeader}>
              <h3 style={styles.slidebarTitle}>Referred Documents</h3>
              <button style={styles.closeButton} onClick={() => setActiveDocsGrievance(null)}>×</button>
            </div>
            
            <div style={{ padding: '15px 20px', borderBottom: '1px solid #e2e8f0', backgroundColor: '#f8fafc' }}>
              <button 
                style={{ ...styles.approveButton, width: '100%' }}
                onClick={() => handleGenerateBriefing(activeDocsGrievance)}
                disabled={briefingLoading}
              >
                {briefingLoading ? "⏳ Generating Action Plan (this may take a moment)..." : "📝 Generate Field Officer Briefing"}
              </button>
            </div>

            <div style={styles.slidebarContent}>
              {briefingNote !== null && (
                <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#e0f2fe', borderRadius: '8px', border: '1px solid #bae6fd' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#0369a1' }}>Generated Briefing Note</h4>
                  <div style={{ fontSize: '13px', lineHeight: '1.6', color: '#0f172a' }}>
                    {typeof briefingNote === 'string' ? (
                      <ReactMarkdown>{briefingNote}</ReactMarkdown>
                    ) : JSON.stringify(briefingNote, null, 2)}
                  </div>
                </div>
              )}

              {activeDocsGrievance.retrieved_context.map((ctx, idx) => (
                <div key={idx} style={styles.contextItem}>
                  <span style={styles.contextSource}>
                    {ctx.metadata?.title || 'Policy Document'}
                  </span>
                  <p style={styles.contextText}>{ctx.text || ctx}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Modal for Attached Image */}
      {activeImageGrievance && (
        <div style={styles.slidebarOverlay} onClick={() => setActiveImageGrievance(null)}>
          <div style={styles.imageModal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.slidebarHeader}>
              <h3 style={styles.slidebarTitle}>Attached Picture</h3>
              <button style={styles.closeButton} onClick={() => setActiveImageGrievance(null)}>×</button>
            </div>
            <div style={{ padding: '20px', textAlign: 'center' }}>
              <img 
                src={`http://localhost:8000/api/v1/grievances/${activeImageGrievance.id}/image`} 
                alt="Grievance Attachment" 
                style={{ maxWidth: '100%', maxHeight: '70vh', borderRadius: '8px' }} 
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Vanilla CSS in JS for Government Minimalism
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
  grid: {
    display: "flex",
    flexDirection: "column",
    gap: "24px",
  },
  card: {
    backgroundColor: "#ffffff",
    border: "1px solid #e0e4e8",
    borderRadius: "8px",
    padding: "20px",
    boxShadow: "0 4px 6px rgba(0,0,0,0.04)",
    display: "flex",
    flexDirection: "column",
    transition: "transform 0.2s ease",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "16px",
    borderBottom: "1px solid #f1f5f9",
    paddingBottom: "12px",
  },
  cardBody: {
    display: "flex",
    flexDirection: "row",
    gap: "32px",
    alignItems: "stretch",
  },
  contentColumn: {
    flex: 1,
    minWidth: "0", /* Prevents flex children from overflowing */
  },
  responseColumn: {
    flex: 2, /* 2/3 of the space for the response and action */
    minWidth: "0",
    display: "flex",
    flexDirection: "column",
  },
  category: {
    margin: "0 0 4px 0",
    fontSize: "18px",
    fontWeight: "600",
    color: "#111827",
  },
  badgeContainer: {
    display: "flex",
    gap: "8px",
  },
  badge: {
    fontSize: "11px",
    fontWeight: "700",
    padding: "4px 8px",
    borderRadius: "4px",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  date: {
    fontSize: "13px",
    color: "#6b7280",
    margin: "0",
  },
  contentSection: {
    marginBottom: "16px",
  },
  sectionTitle: {
    fontSize: "12px",
    fontWeight: "700",
    color: "#4b5563",
    textTransform: "uppercase",
    margin: "0 0 8px 0",
    letterSpacing: "0.5px",
  },
  draftHeaderRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "8px",
  },
  referredLink: {
    background: "none",
    border: "none",
    color: "#0056b3",
    fontSize: "12px",
    fontWeight: "600",
    cursor: "pointer",
    padding: 0,
    textDecoration: "underline",
  },
  description: {
    fontSize: "14px",
    color: "#374151",
    margin: 0,
    fontStyle: "italic",
    lineHeight: "1.5",
    paddingLeft: "12px",
    borderLeft: "3px solid #cbd5e1",
  },
  aiDraft: {
    backgroundColor: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "6px",
    padding: "12px",
    fontSize: "14px",
    color: "#1e293b",
    lineHeight: "1.6",
    minHeight: "80px",
    display: "flex",
    flexDirection: "column",
  },
  responseEditor: {
    width: "100%",
    minHeight: "150px", /* Increased height for wider input */
    padding: "8px",
    border: "1px solid #cbd5e1",
    borderRadius: "4px",
    fontFamily: "inherit",
    fontSize: "14px",
    resize: "vertical",
    boxSizing: "border-box",
  },
  draftPending: {
    margin: 0,
    color: "#94a3b8",
    fontStyle: "italic",
    animation: "pulse 2s infinite",
  },
  contextBox: {
    backgroundColor: "#f1f5f9",
    border: "1px solid #e2e8f0",
    borderRadius: "6px",
    padding: "10px",
    maxHeight: "150px",
    overflowY: "auto",
  },
  contextItem: {
    marginBottom: "10px",
    paddingBottom: "10px",
    borderBottom: "1px solid #cbd5e1",
  },
  contextSource: {
    display: "block",
    fontSize: "11px",
    fontWeight: "bold",
    color: "#003366",
    marginBottom: "4px",
  },
  contextText: {
    fontSize: "12px",
    color: "#475569",
    margin: 0,
    lineHeight: "1.4",
  },
  actionSection: {
    marginTop: "auto",
    paddingTop: "16px",
    borderTop: "1px solid #f1f5f9",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  actionButtons: {
    display: "flex",
    gap: "12px",
    alignItems: "center",
  },
  statusText: {
    fontSize: "14px",
    fontWeight: "600",
  },
  approveButton: {
    backgroundColor: "#003366",
    color: "white",
    border: "none",
    padding: "8px 16px",
    borderRadius: "4px",
    fontSize: "14px",
    fontWeight: "600",
    transition: "background-color 0.2s",
  },
  loading: {
    textAlign: "center",
    padding: "40px",
    fontSize: "18px",
    color: "#64748b",
  },
  error: {
    backgroundColor: "#fee2e2",
    color: "#b91c1c",
    padding: "12px",
    borderRadius: "6px",
    marginBottom: "20px",
  },
  emptyState: {
    gridColumn: "1 / -1",
    textAlign: "center",
    padding: "60px 20px",
    backgroundColor: "#f8fafc",
    borderRadius: "8px",
    color: "#64748b",
    fontSize: "16px",
    border: "2px dashed #cbd5e1",
  },
  slidebarOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.4)',
    zIndex: 1000,
    display: 'flex',
    justifyContent: 'flex-end',
  },
  slidebar: {
    width: '450px',
    backgroundColor: '#fff',
    height: '100%',
    boxShadow: '-4px 0 15px rgba(0,0,0,0.1)',
    display: 'flex',
    flexDirection: 'column',
  },
  slidebarHeader: {
    padding: '20px',
    borderBottom: '1px solid #e2e8f0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
  },
  slidebarTitle: {
    margin: 0,
    fontSize: '18px',
    color: '#003366',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '28px',
    lineHeight: '1',
    cursor: 'pointer',
    color: '#64748b',
    padding: '0 8px',
  },
  slidebarContent: {
    padding: '20px',
    overflowY: 'auto',
    flex: 1,
  },
  imageButton: {
    marginTop: '12px',
    backgroundColor: '#f1f5f9',
    color: '#0056b3',
    border: '1px solid #cbd5e1',
    padding: '6px 12px',
    borderRadius: '4px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    transition: 'background-color 0.2s',
  },
  imageModal: {
    width: '600px',
    maxWidth: '90%',
    backgroundColor: '#fff',
    borderRadius: '8px',
    margin: 'auto',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
  }
};

export default GrievanceDashboard;
