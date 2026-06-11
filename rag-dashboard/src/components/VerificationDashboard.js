import React, { useState } from "react";

const VerificationDashboard = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setResult(null);
    setError(null);
  };

  const handleVerify = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Assumes backend is running on 8000 as configured in App.js/general setup
      const response = await fetch("http://localhost:8000/api/v1/verification/verify-pipeline", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Verification failed with status: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      setError("Failed to verify document. Ensure backend is running and file is valid.");
    } finally {
      setLoading(false);
    }
  };

  const getImageUrl = (absolutePath) => {
    if (!absolutePath) return null;
    // Extract "category/filename" from "D:\NH_RAG\storage\category\filename.png"
    const parts = absolutePath.split(/[\/\\]storage[\/\\]/);
    if (parts.length > 1) {
        return `http://localhost:8000/api/v1/verification/storage/${parts[1].replace(/\\/g, '/')}`;
    }
    return null;
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.header}>🔍 Document Verification Agent</h2>
      <p style={styles.subtext}>Upload an Aadhaar, PAN, or Passport for AI-powered verification.</p>

      {/* Upload Section */}
      <div style={styles.uploadSection}>
        <input type="file" accept="image/*,.pdf" onChange={handleFileChange} style={styles.fileInput} />
        <button
          onClick={handleVerify}
          disabled={!file || loading}
          style={{ ...styles.verifyButton, opacity: !file || loading ? 0.6 : 1 }}
        >
          {loading ? "Processing..." : "Verify Document"}
        </button>
      </div>

      {error && <div style={styles.errorBox}>{error}</div>}

      {/* Results Section */}
      {result && (
        <div style={styles.resultsGrid}>
          {/* Document Image Card */}
          {result.normalized_image_path && (
            <div style={styles.card}>
              <h3>Scanned Document</h3>
              <img 
                src={getImageUrl(result.normalized_image_path)} 
                alt="Document Preview" 
                style={styles.previewImage} 
              />
            </div>
          )}

          {/* Decision Card */}
          <div style={styles.card}>
            <h3>Final Decision</h3>
            <div
              style={{
                ...styles.decisionBadge,
                backgroundColor: result.decision_result.decision === "APPROVED" ? "#28a745" : "#dc3545",
              }}
            >
              {result.decision_result.decision}
            </div>
            <p><strong>Reason:</strong> {(result.decision_result.reasons || []).join(', ') || 'N/A'}</p>
            <p><strong>Confidence:</strong> {result.decision_result.confidence?.toFixed(2)}</p>
          </div>

          {/* Classification & Fields Card */}
          <div style={styles.card}>
            <h3>Classification & Data</h3>
            <p><strong>Type:</strong> <span style={styles.badge}>{result.document_type}</span></p>
            <div style={styles.fieldsContainer}>
              {Object.entries(result.extracted_fields || {}).map(([key, value]) => (
                <div key={key} style={styles.fieldRow}>
                  <span style={styles.fieldKey}>{key}:</span>
                  <span style={styles.fieldValue}>{value || "N/A"}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Checks Card */}
          <div style={styles.card}>
            <h3>Verification Checks</h3>
            <div style={styles.checksContainer}>
              <h4>Passed Checks</h4>
              <ul style={styles.passedList}>
                {(result.verification_result?.passed_checks || []).map((check, i) => (
                  <li key={i}>✅ {check}</li>
                ))}
              </ul>
              <h4>Failed Checks</h4>
              <ul style={styles.failedList}>
                {(result.verification_result?.failed_checks || []).map((check, i) => (
                  <li key={i}>❌ {check}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Fraud Detection Card */}
          <div style={styles.card}>
            <h3>Fraud & Quality Metrics</h3>
            <p><strong>Tampering Detected:</strong> {result.fraud_result?.fraud_flags?.length > 0 ? `Yes ⚠️ (${result.fraud_result.fraud_flags.join(', ')})` : "No ✅"}</p>
            <p><strong>Blur (Laplacian Var):</strong> {result.fraud_result?.signals?.blur?.laplacian_variance?.toFixed(2)}</p>
            <p><strong>Overexposure:</strong> {(result.fraud_result?.signals?.overexposure?.overexposed_fraction * 100)?.toFixed(1)}%</p>
            <p><strong>Underexposure:</strong> {(result.fraud_result?.signals?.underexposure?.underexposed_fraction * 100)?.toFixed(1)}%</p>
          </div>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: "20px",
    backgroundColor: "#fff",
    borderRadius: "12px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
  },
  header: {
    marginTop: 0,
    color: "#333",
  },
  subtext: {
    color: "#666",
    marginBottom: "20px",
  },
  uploadSection: {
    display: "flex",
    gap: "10px",
    marginBottom: "30px",
    alignItems: "center",
  },
  fileInput: {
    padding: "10px",
    border: "1px solid #ccc",
    borderRadius: "6px",
    flex: 1,
  },
  verifyButton: {
    padding: "12px 24px",
    backgroundColor: "#17a2b8",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontWeight: "bold",
  },
  errorBox: {
    padding: "15px",
    backgroundColor: "#f8d7da",
    color: "#721c24",
    borderRadius: "6px",
    marginBottom: "20px",
  },
  resultsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
    gap: "20px",
  },
  card: {
    padding: "20px",
    border: "1px solid #eee",
    borderRadius: "8px",
    backgroundColor: "#fafafa",
  },
  previewImage: {
    width: "100%",
    maxHeight: "300px",
    objectFit: "contain",
    borderRadius: "8px",
    border: "1px solid #ddd",
    backgroundColor: "#fff",
  },
  decisionBadge: {
    display: "inline-block",
    padding: "8px 16px",
    color: "#fff",
    borderRadius: "20px",
    fontWeight: "bold",
    marginBottom: "10px",
  },
  badge: {
    padding: "4px 8px",
    backgroundColor: "#e9ecef",
    borderRadius: "4px",
    fontSize: "0.9em",
    fontWeight: "bold",
  },
  fieldsContainer: {
    marginTop: "15px",
  },
  fieldRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "8px 0",
    borderBottom: "1px solid #eee",
  },
  fieldKey: {
    fontWeight: "bold",
    color: "#555",
    textTransform: "capitalize",
  },
  fieldValue: {
    color: "#333",
  },
  checksContainer: {
    marginTop: "10px",
  },
  passedList: {
    listStyleType: "none",
    padding: 0,
    color: "#28a745",
  },
  failedList: {
    listStyleType: "none",
    padding: 0,
    color: "#dc3545",
  },
};

export default VerificationDashboard;
