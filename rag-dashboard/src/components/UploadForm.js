import React, { useState } from "react";
import authAxios from "../utils/authAxios";

function UploadForm({ setJobId }) {
  const [form, setForm] = useState({
    file: null,
    title: "",
    issuing_authority: "",
    jurisdiction: "central",
    document_type: "policy",
    primary_language: "en",
    document_number: "",
    department_code: "",
    state_origin: "",
    security_level: "public",
    version_label: "",
    publication_date: "",
    effective_date: ""
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];

    if (!file) return;

    if (file.type !== "application/pdf") {
      setError("Only PDF files are allowed");
      return;
    }

    if (file.size > 40 * 1024 * 1024) {
      setError("File size must be under 40MB");
      return;
    }

    setError("");
    setForm((prev) => ({ ...prev, file }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!form.file) {
      setError("File is required");
      return;
    }

    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const formData = new FormData();
      Object.keys(form).forEach((key) => {
        formData.append(key, form[key]);
      });

      const res = await authAxios.post("/api/ingest/upload", formData);
      const jobId = res.data.job_id;

      setJobId(jobId);
      setSuccess("Upload successful. Processing started.");

    } catch (err) {
      const backendError = err.response?.data?.detail;

      if (Array.isArray(backendError)) {
        setError(backendError.map((e) => e.msg).join(", "));
      } else {
        setError(backendError || "Upload failed. Try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <form onSubmit={handleSubmit} style={styles.container}>

        <h2 style={styles.heading}>Document Upload</h2>

        {/* FILE */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>File Upload</h4>

          <div style={styles.fileUploadWrapper}>
            <input type="file" onChange={handleFileChange} style={styles.fileInput} />
            {form.file && (
              <p style={styles.fileName}>Selected: {form.file.name}</p>
            )}
          </div>
        </div>

        {/* BASIC */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>Basic Information</h4>

          <div style={styles.grid}>
            <input style={styles.input} name="title" placeholder="Document Title" value={form.title} onChange={handleChange} required />
            <input style={styles.input} name="document_number" placeholder="Document Number" value={form.document_number} onChange={handleChange} />
          </div>
        </div>

        {/* GOVERNMENT */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>Government Metadata</h4>

          <div style={styles.grid}>
            <input style={styles.input} name="issuing_authority" placeholder="Issuing Authority" value={form.issuing_authority} onChange={handleChange} required />
            <input style={styles.input} name="department_code" placeholder="Department Code" value={form.department_code} onChange={handleChange} />

            <select style={styles.select} name="jurisdiction" value={form.jurisdiction} onChange={handleChange}>
              <option value="central">Central</option>
              <option value="state">State</option>
              <option value="municipal">Municipal</option>
            </select>

            <input style={styles.input} name="state_origin" placeholder="State" value={form.state_origin} onChange={handleChange} />
          </div>
        </div>

        {/* CLASSIFICATION */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>Classification</h4>

          <div style={styles.grid}>
            <select style={styles.select} name="document_type" value={form.document_type} onChange={handleChange}>
              <option value="policy">Policy</option>
              <option value="act">Act</option>
              <option value="rule">Rule</option>
              <option value="notification">Notification</option>
            </select>

            <select style={styles.select} name="security_level" value={form.security_level} onChange={handleChange}>
              <option value="public">Public</option>
              <option value="internal">Internal</option>
              <option value="confidential">Confidential</option>
            </select>
          </div>
        </div>

        {/* LANGUAGE */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>Language</h4>
          <input style={styles.input} name="primary_language" value={form.primary_language} onChange={handleChange} />
        </div>

        {/* DATES */}
        <div style={styles.section}>
          <h4 style={styles.sectionTitle}>Dates & Version</h4>

          <div style={styles.grid}>
            <input style={styles.input} type="date" name="publication_date" value={form.publication_date} onChange={handleChange} />
            <input style={styles.input} type="date" name="effective_date" value={form.effective_date} onChange={handleChange} />
            <input style={styles.input} name="version_label" placeholder="Version" value={form.version_label} onChange={handleChange} />
          </div>
        </div>

        {/* FEEDBACK */}
        {error && <p style={styles.error}>{error}</p>}
        {success && <p style={styles.success}>{success}</p>}

        <button style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }} type="submit" disabled={loading}>
          {loading ? "Processing..." : "Upload & Process"}
        </button>

      </form>
    </div>
  );
}

const styles = {
  page: {}, // Removed layout wrappers as App.js card handles it

  container: {
    display: "flex",
    flexDirection: "column",
    gap: "24px"
  },

  heading: {
    fontSize: "24px",
    fontWeight: "700",
    color: "#0f172a",
    margin: "0 0 8px 0"
  },

  section: {
    border: "1px solid #e2e8f0",
    borderRadius: "12px",
    padding: "24px",
    background: "#f8fafc"
  },

  sectionTitle: {
    marginBottom: "16px",
    fontSize: "16px",
    fontWeight: "600",
    color: "#1e293b",
    margin: "0 0 16px 0"
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

  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px"
  },

  input: {
    padding: "14px 16px",
    borderRadius: "8px",
    border: "1.5px solid #cbd5e1",
    fontSize: "14px",
    background: "#fff",
    outline: "none",
    transition: "border-color 0.2s",
    boxSizing: "border-box",
    width: "100%"
  },

  select: {
    padding: "14px 16px",
    borderRadius: "8px",
    border: "1.5px solid #cbd5e1",
    fontSize: "14px",
    background: "#fff",
    outline: "none",
    transition: "border-color 0.2s",
    boxSizing: "border-box",
    width: "100%",
    cursor: "pointer"
  },

  button: {
    padding: "16px",
    borderRadius: "12px",
    border: "none",
    background: "#003366",
    color: "#fff",
    fontWeight: "600",
    fontSize: "16px",
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(0, 51, 102, 0.2)",
    transition: "all 0.2s ease",
    marginTop: "8px"
  },

  buttonDisabled: {
    opacity: 0.7,
    cursor: "not-allowed"
  },

  error: {
    color: "#ef4444",
    fontSize: "14px",
    background: "#fef2f2",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #fee2e2",
    margin: 0
  },

  success: {
    color: "#15803d",
    fontSize: "14px",
    background: "#f0fdf4",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #dcfce7",
    margin: 0
  },

  fileName: {
    fontSize: "13px",
    color: "#64748b",
    margin: "4px 0 0 0",
    fontWeight: "500"
  }
};

export default UploadForm;