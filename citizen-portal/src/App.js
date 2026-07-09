import React, { useState } from "react";
import axios from "axios";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const App = () => {
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
      const res = await axios.get(`${API_URL}/api/v1/grievances/${trackId}`);
      setTrackedGrievance(res.data);
    } catch (err) {
      setTrackError(err.response?.data?.detail || "Could not find grievance");
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
    <div style={styles.page}>
      <div style={styles.card}>
        <h2 style={styles.title}>🏛️ Citizen Grievance Portal</h2>
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

        <hr style={{margin: '0', border: 'none', borderTop: '1px solid #e5e7eb'}} />
        
        <div style={styles.section}>
          <h2 style={{...styles.title, fontSize: '20px'}}>🔍 Track Your Grievance</h2>
          <p style={{...styles.subtitle, marginBottom: '16px'}}>Enter your unique Ticket ID to check the status and read the official response.</p>
          
          <form onSubmit={handleTrack} style={{display: 'flex', gap: '10px'}}>
            <input 
              type="text" 
              placeholder="Enter Ticket ID (e.g. 123e4567-...)" 
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
  );
};

const styles = {
  page: {
    fontFamily: "'Inter', 'Segoe UI', sans-serif",
    background: "#f4f7fb",
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "32px"
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
