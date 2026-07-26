import React, { useState } from "react";
import axios from "axios";
import EntitlementDashboard from "./EntitlementDashboard";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const App = () => {
  const [activePortal, setActivePortal] = useState("grievance");
  const [category, setCategory] = useState("Sanitation");
  const [description, setDescription] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const [trackId, setTrackId] = useState("");
  const [trackedGrievance, setTrackedGrievance] = useState(null);
  const [trackError, setTrackError] = useState("");
  const [trackLoading, setTrackLoading] = useState(false);

  const handleTrack = async (e) => {
    e.preventDefault();
    setTrackLoading(true);
    setTrackError("");
    setTrackedGrievance(null);
    try {
      if (trackId.startsWith("APP-")) {
        // Simulate Entitlement Application Tracking
        setTrackedGrievance({
          category: "Entitlement Scheme Application",
          status: "PENDING",
          description: `Tracking ID: ${trackId}`,
          official_response: "Your application is currently under review by the official authorities. All required documents have been verified. Please check back later for updates."
        });
      } else {
        const res = await axios.get(`${API_URL}/api/v1/grievances/${trackId}`);
        setTrackedGrievance(res.data);
      }
    } catch (err) {
      setTrackError(err.response?.data?.detail || "Could not find record with this Tracking ID");
    } finally {
      setTrackLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSuccess("");
    setError("");

    try {
      // Send as form data to match the FastAPI Form(...) dependencies
      const formData = new FormData();
      formData.append("category", category);
      formData.append("description", description);
      if (imageFile) {
        formData.append("attachments", imageFile);
      }

      const response = await axios.post(`${API_URL}/api/v1/grievances/`, formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });

      setSuccess(`Grievance submitted successfully! Ticket ID: ${response.data.ticket_id}`);
      setDescription(""); // clear form
      setImageFile(null); // clear image
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to submit grievance.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ backgroundColor: '#fff', padding: '15px 40px', display: 'flex', gap: '15px', borderBottom: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', position: 'sticky', top: 0, zIndex: 100 }}>
        <button 
          onClick={() => setActivePortal('grievance')} 
          style={{ padding: '10px 24px', border: 'none', borderRadius: '6px', cursor: 'pointer', backgroundColor: activePortal === 'grievance' ? '#2563eb' : '#f1f5f9', color: activePortal === 'grievance' ? '#fff' : '#475569', fontWeight: 'bold', fontSize: '15px', transition: 'all 0.2s' }}
        >
          Grievance Agent
        </button>
        <button 
          onClick={() => setActivePortal('entitlement')} 
          style={{ padding: '10px 24px', border: 'none', borderRadius: '6px', cursor: 'pointer', backgroundColor: activePortal === 'entitlement' ? '#2563eb' : '#f1f5f9', color: activePortal === 'entitlement' ? '#fff' : '#475569', fontWeight: 'bold', fontSize: '15px', transition: 'all 0.2s' }}
        >
          Entitlement Agent
        </button>
        <button 
          onClick={() => setActivePortal('tracking')} 
          style={{ padding: '10px 24px', border: 'none', borderRadius: '6px', cursor: 'pointer', backgroundColor: activePortal === 'tracking' ? '#2563eb' : '#f1f5f9', color: activePortal === 'tracking' ? '#fff' : '#475569', fontWeight: 'bold', fontSize: '15px', transition: 'all 0.2s' }}
        >
          Citizen Requests
        </button>
      </div>

      {activePortal === 'grievance' ? (
        <div style={styles.page}>
          <div style={styles.card}>
            <h2 style={styles.title}>🏛️ Grievance Citizen Portal</h2>
            <p style={styles.subtitle}>Submit a complaint for automated AI processing and official review.</p>

        {success && <div style={styles.successBadge}>{success}</div>}
        {error && <div style={styles.errorBadge}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.section}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Category</label>
              <select 
                value={category} 
                onChange={(e) => setCategory(e.target.value)}
                style={styles.input}
              >
                <option value="Sanitation">Sanitation</option>
                <option value="Water Supply">Water Supply</option>
                <option value="Roads">Roads / Potholes</option>
                <option value="Electricity">Electricity</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Please describe your issue in detail (optional if attaching a picture)..."
                style={{...styles.input, height: "120px", resize: "vertical"}}
                required={!imageFile}
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Add a pic</label>
              <div style={styles.fileUploadWrapper}>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setImageFile(e.target.files[0])}
                  style={styles.fileInput}
                />
              </div>
            </div>
          </div>

          <button type="submit" disabled={loading || (!description.trim() && !imageFile)} style={styles.submitButton}>
            {loading ? "Submitting to AI..." : "Submit Grievance"}
          </button>
        </form>

      </div>
        </div>
      ) : activePortal === 'entitlement' ? (
        <EntitlementDashboard />
      ) : (
        <div style={styles.page}>
          <div style={styles.card}>
            <div style={styles.section}>
              <h2 style={{...styles.title, fontSize: '20px'}}>🔍 Track Your Request</h2>
              <p style={{...styles.subtitle, marginBottom: '16px'}}>Enter your unique Tracking ID to check the status of your Grievance or Entitlement Application.</p>
              
              <form onSubmit={handleTrack} style={{display: 'flex', gap: '10px'}}>
                <input 
                  type="text" 
                  placeholder="Enter Tracking ID (e.g. 123e4567-... or APP-...)" 
                  value={trackId} 
                  onChange={(e) => setTrackId(e.target.value)}
                  style={{...styles.input, flex: 1}}
                  required
                />
                <button type="submit" disabled={trackLoading} style={{...styles.submitButton, marginTop: 0}}>
                  {trackLoading ? "Searching..." : "Track"}
                </button>
              </form>
            </div>

            {trackError && <div style={{...styles.errorBadge, marginTop: '16px'}}>{trackError}</div>}

            {trackedGrievance && (
              <div style={{marginTop: '20px', padding: '16px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '10px'}}>
                  <strong style={{fontSize: '15px', color: '#1e293b'}}>{trackedGrievance.category}</strong>
                  <span style={{
                    backgroundColor: trackedGrievance.status === 'APPROVED' ? '#dcfce7' : '#fef08a',
                    color: trackedGrievance.status === 'APPROVED' ? '#166534' : '#854d0e',
                    padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold'
                  }}>
                    {trackedGrievance.status}
                  </span>
                </div>
                <p style={{fontSize: '14px', color: '#475569', marginBottom: '16px', fontStyle: 'italic'}}>"{trackedGrievance.description}"</p>
                
                {trackedGrievance.official_response ? (
                  <div style={{backgroundColor: '#ffffff', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #3b82f6', boxShadow: '0 1px 3px rgba(0,0,0,0.05)'}}>
                    <h5 style={{margin: '0 0 8px 0', color: '#1e3a8a', fontSize: '14px'}}>Official Response:</h5>
                    <p style={{margin: 0, fontSize: '14px', whiteSpace: 'pre-wrap', color: '#334155'}}>{trackedGrievance.official_response}</p>
                  </div>
                ) : (
                  <p style={{fontSize: '13px', color: '#94a3b8', fontStyle: 'italic', margin: 0}}>Pending official review...</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const styles = {
  page: {
    fontFamily: "'Inter', 'Segoe UI', sans-serif",
    background: "#f4f7fb",
    minHeight: "calc(100vh - 72px)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "flex-start",
    padding: "48px 32px"
  },
  card: {
    backgroundColor: "#ffffff",
    padding: "32px",
    borderRadius: "16px",
    boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
    border: "1px solid #e2e8f0",
    width: "100%",
    maxWidth: "800px",
    margin: "0 auto",
    display: "flex",
    flexDirection: "column",
    gap: "24px"
  },
  section: {
    border: "1px solid #e2e8f0",
    borderRadius: "12px",
    padding: "24px",
    background: "#f8fafc",
    display: "flex",
    flexDirection: "column",
    gap: "16px"
  },
  title: {
    margin: "0",
    color: "#0f172a",
    fontSize: "24px",
    fontWeight: "700"
  },
  subtitle: {
    margin: "0",
    color: "#64748b",
    fontSize: "14px"
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "16px"
  },
  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "8px"
  },
  label: {
    fontSize: "14px",
    fontWeight: "600",
    color: "#1e293b"
  },
  input: {
    padding: "14px 16px",
    borderRadius: "8px",
    border: "1.5px solid #cbd5e1",
    fontSize: "14px",
    background: "#fff",
    outline: "none",
    transition: "border-color 0.2s",
    width: "100%",
    boxSizing: "border-box"
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
    cursor: "pointer"
  },
  submitButton: {
    padding: "16px",
    borderRadius: "12px",
    border: "none",
    background: "#003366",
    color: "#fff",
    fontWeight: "600",
    fontSize: "16px",
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(0, 51, 102, 0.2)",
    transition: "all 0.2s ease"
  },
  successBadge: {
    backgroundColor: "#f0fdf4",
    color: "#15803d",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #dcfce7",
    fontSize: "14px",
    margin: 0
  },
  errorBadge: {
    backgroundColor: "#fef2f2",
    color: "#ef4444",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #fee2e2",
    fontSize: "14px",
    margin: 0
  }
};

export default App;
