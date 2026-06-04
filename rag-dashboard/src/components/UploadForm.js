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

          <input type="file" onChange={handleFileChange} />

          {form.file && (
            <p style={styles.fileName}>{form.file.name}</p>
          )}
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

            <select style={styles.input} name="jurisdiction" value={form.jurisdiction} onChange={handleChange}>
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
            <select style={styles.input} name="document_type" value={form.document_type} onChange={handleChange}>
              <option value="policy">Policy</option>
              <option value="act">Act</option>
              <option value="rule">Rule</option>
              <option value="notification">Notification</option>
            </select>

            <select style={styles.input} name="security_level" value={form.security_level} onChange={handleChange}>
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

        <button style={styles.button} type="submit" disabled={loading}>
          {loading ? "Processing..." : "Upload & Process"}
        </button>

      </form>
    </div>
  );
}

const styles = {
  page: {
    display: "flex",
    justifyContent: "center",
    padding: "30px",
    minHeight: "100vh",
    background: "#f4f6f9"
  },

  container: {
    width: "100%",
    padding: "25px",
    borderRadius: "8px",
    background: "#ffffff",
    border: "1px solid #dcdfe6",
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
    display: "flex",
    flexDirection: "column",
    gap: "18px"
  },

  heading: {
    fontSize: "20px",
    fontWeight: "600",
    color: "#1e293b"
  },

  section: {
    border: "1px solid #e0e0e0",
    borderRadius: "6px",
    padding: "16px",
    background: "#fafafa"
  },

  sectionTitle: {
    marginBottom: "10px",
    fontSize: "14px",
    fontWeight: "600",
    color: "#333"
  },

  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "12px"
  },

  input: {
    padding: "10px",
    borderRadius: "6px",
    border: "1px solid #cfd6dd",
    fontSize: "14px"
  },

  button: {
    padding: "12px",
    borderRadius: "6px",
    border: "none",
    background: "#1f3a5f",
    color: "#fff",
    fontWeight: "600",
    cursor: "pointer"
  },

  error: {
    color: "#c62828",
    fontSize: "13px"
  },

  success: {
    color: "#2e7d32",
    fontSize: "13px"
  },

  fileName: {
    fontSize: "12px",
    color: "#555",
    marginTop: "5px"
  }
};

export default UploadForm;