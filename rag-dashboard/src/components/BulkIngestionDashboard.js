/** rag-dashboard/src/components/BulkIngestionDashboard.js */

import React, { useState } from "react";
import authAxios from "../utils/authAxios";

function BulkIngestionDashboard({ goBack }) {

  const [pdfFiles, setPdfFiles] = useState([]);
  const [jsonFiles, setJsonFiles] = useState([]);

  const [pairs, setPairs] = useState([]);
  const [errors, setErrors] = useState([]);

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  /**
   * 📁 HANDLE FOLDER UPLOAD
   */
  const handleFolderUpload = (e) => {
    const files = Array.from(e.target.files);

    const pdfs = [];
    const jsons = [];

    files.forEach((file) => {
      if (file.name.toLowerCase().endsWith(".pdf")) {
        pdfs.push(file);
      } else if (file.name.toLowerCase().endsWith(".json")) {
        jsons.push(file);
      }
    });

    setPdfFiles(pdfs);
    setJsonFiles(jsons);

    setPairs([]);
    setErrors([]);
    setSuccess("");
  };

  /**
   * 🔗 MATCHING LOGIC
   */
  const matchFiles = () => {
    const matched = [];
    const errorList = [];

    const jsonMap = {};

    jsonFiles.forEach((file) => {
      const baseName = file.name.replace(".json", "");
      jsonMap[baseName] = file;
    });

    pdfFiles.forEach((pdf) => {
      const baseName = pdf.name.replace(".pdf", "");

      if (!jsonMap[baseName]) {
        // Provide a dummy JSON file since the backend will now auto-generate the metadata for us
        const dummyBlob = new Blob(['{}'], { type: 'application/json' });
        const newJson = new File([dummyBlob], `${baseName}.json`, { type: 'application/json' });
        jsonMap[baseName] = newJson;
        // Update the UI counter to reflect this newly generated JSON
        setJsonFiles(prev => {
          if (!prev.find(f => f.name === newJson.name)) {
            return [...prev, newJson];
          }
          return prev;
        });
      }

      matched.push({
        id: baseName,
        pdf,
        json: jsonMap[baseName],
        status: "READY",
        error: "",
        job_id: null,
        progress: 0 // 🔥 NEW
      });
    });

    jsonFiles.forEach((json) => {
      const baseName = json.name.replace(".json", "");
      const exists = pdfFiles.find(
        (pdf) => pdf.name.replace(".pdf", "") === baseName
      );

      if (!exists) {
        errorList.push(`❌ No PDF for metadata: ${json.name}`);
      }
    });

    setPairs(matched);
    setErrors(errorList);
  };

  /**
   * 🧠 METADATA VALIDATION
   */
  const validateAndFixMetadata = async (pair) => {
    try {
      const text = await pair.json.text();
      JSON.parse(text);
      return { valid: true };
    } catch {
      return { valid: false, error: "Invalid JSON" };
    }
  };

  /**
   * 🔄 UPDATE STATUS (NOW SUPPORTS PROGRESS)
   */
  const updateStatus = (id, status, error = "", job_id = null, progress = null) => {
    setPairs((prev) =>
      prev.map((p) =>
        p.id === id
          ? {
              ...p,
              status,
              error,
              job_id: job_id ?? p.job_id,
              progress: progress ?? p.progress
            }
          : p
      )
    );
  };

  /**
   * 🔁 POLL BACKEND STATUS (REAL SOURCE OF TRUTH + PROGRESS)
   */
  const pollJobStatus = (id, job_id) => {
    const interval = setInterval(async () => {
      try {
        const res = await authAxios.get(`/api/ingest/status/${job_id}`);

        const data = res.data;

        // 🔥 UPDATE STATUS + PROGRESS
        updateStatus(
          id,
          data.status,
          data.error || "",
          job_id,
          data.progress || 0
        );

        if (data.status === "COMPLETED" || data.status === "FAILED") {
          clearInterval(interval);
        }

      } catch {
        updateStatus(id, "FAILED", "Status check failed");
        clearInterval(interval);
      }
    }, 2000);
  };

  /**
   * 🚀 SEQUENTIAL INGESTION
   */
  const handleSubmit = async () => {
    if (pairs.length === 0) {
      setErrors(["No valid pairs to upload"]);
      return;
    }

    setLoading(true);
    setErrors([]);
    setSuccess("");

    let processed = 0;

    for (let i = 0; i < pairs.length; i++) {
      const pair = pairs[i];

      if (pair.status !== "READY") continue;

      const validation = await validateAndFixMetadata(pair);

      if (!validation.valid) {
        updateStatus(pair.id, "FAILED", validation.error);
        continue;
      }

      updateStatus(pair.id, "UPLOADING");

      try {
        const formData = new FormData();
        formData.append("files", pair.pdf);
        formData.append("metadata_files", pair.json);

        const res = await authAxios.post("/api/ingest/bulk-upload", formData);

        const data = res.data;
        
        // axios automatically throws on 4xx/5xx, no need for res.ok check
        const job = data.jobs[0];

        updateStatus(pair.id, "PROCESSING", "", job.job_id);

        pollJobStatus(pair.id, job.job_id);

        processed++;

      } catch {
        updateStatus(pair.id, "FAILED", "Upload failed");
      }
    }

    setLoading(false);
    setSuccess(`✅ Submitted ${processed} files for processing`);
  };

  /**
   * 🔄 RETRY FAILED UPLOADS
   */
  const handleRetryFailed = () => {
    let hasFailed = false;
    setPairs(currentPairs => {
      return currentPairs.map(p => {
        if (p.status === "FAILED") {
          hasFailed = true;
          return { ...p, status: "READY", error: "", progress: 0 };
        }
        return p;
      });
    });

    if (hasFailed) {
      setErrors([]);
      setSuccess("Failed files are marked as READY. Click 'Submit for Ingestion' to try again.");
    } else {
      setErrors(["No failed uploads to retry"]);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <h2 style={styles.heading}>📦 Bulk Ingestion Dashboard</h2>

        <button onClick={goBack} style={styles.backButton}>
          ← Back to Dashboard
        </button>

        {/* UPLOAD */}
        <div style={styles.uploadBox}>
          <label style={styles.fileDrop}>
            📁 Upload Folder (PDF + JSON)
            <input
              type="file"
              webkitdirectory="true"
              multiple
              onChange={handleFolderUpload}
              hidden
            />
          </label>
        </div>

        {/* INFO */}
        <div style={styles.infoCards}>
          <div style={styles.infoCard}>📄 PDFs: {pdfFiles.length}</div>
          <div style={styles.infoCard}>🧾 JSON: {jsonFiles.length}</div>
        </div>

        <button onClick={matchFiles} style={styles.matchButton}>
          Match Files
        </button>

        {/* ERRORS */}
        {errors.length > 0 && (
          <div style={styles.errorBox}>
            <h4>⚠ Validation Errors</h4>
            {errors.map((err, index) => (
              <p key={index}>{err}</p>
            ))}
          </div>
        )}

        {/* SUCCESS */}
        {success && <div style={styles.successBox}>{success}</div>}

        {/* TABLE */}
        {pairs.length > 0 && (
          <div style={styles.preview}>
            <h4 style={styles.sectionTitle}>📄 Matched Files</h4>

            <table style={styles.table}>
              <thead>
                <tr>
                  <th>PDF</th>
                  <th>JSON</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Error</th>
                </tr>
              </thead>

              <tbody>
              {pairs.map((pair) => (
                <tr key={pair.id} style={styles.row}>
                  
                  <td style={styles.cell}>
                    <div style={styles.fileName}>{pair.pdf.name}</div>
                  </td>

                  <td style={styles.cell}>
                    <div style={styles.fileName}>{pair.json.name}</div>
                  </td>

                  <td style={styles.cell}>
                    <span style={styles.statusBadge}>
                      {pair.status}
                    </span>
                  </td>

                  <td style={styles.cell}>
                    <div style={styles.progressWrapper}>
                      <div style={styles.progressBarContainer}>
                        <div
                          style={{
                            ...styles.progressBarFill,
                            width: `${pair.progress || 0}%`
                          }}
                        />
                      </div>
                      <span style={styles.progressText}>
                        {pair.progress || 0}%
                      </span>
                    </div>
                  </td>

                  <td style={styles.cell}>
                    <span style={styles.errorText}>{pair.error}</span>
                  </td>

                </tr>
              ))}
            </tbody>
            </table>

            <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
              <button
                onClick={handleSubmit}
                style={styles.submitButton}
                disabled={loading}
              >
                {loading ? "Processing..." : "Submit for Ingestion"}
              </button>

              <button
                onClick={handleRetryFailed}
                style={{ ...styles.submitButton, background: "#d97706" }}
                disabled={loading || !pairs.some(p => p.status === "FAILED")}
              >
                🔄 Retry Failed Uploads
              </button>
            </div>
          </div>
        )}
      </div>
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
    width: "1000px",
    padding: "25px",
    borderRadius: "8px",
    background: "#ffffff",
    border: "1px solid #dcdfe6",
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
    display: "flex",
    flexDirection: "column",
    gap: "16px"
  },

  heading: {
    color: "#1e293b",
    fontSize: "20px",
    fontWeight: "600"
  },

  backButton: {
    padding: "8px 12px",
    width: "220px",
    background: "#6c757d",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer"
  },

  uploadBox: {
    display: "flex",
    justifyContent: "center"
  },

  fileDrop: {
    padding: "20px",
    borderRadius: "6px",
    border: "2px dashed #cfd6dd",
    color: "#374151",
    cursor: "pointer",
    textAlign: "center",
    width: "100%",
    background: "#fafafa"
  },

  infoCards: {
    display: "flex",
    gap: "12px"
  },

  infoCard: {
    flex: 1,
    padding: "10px",
    borderRadius: "6px",
    background: "#f9fafb",
    border: "1px solid #e5e7eb",
    color: "#1e293b",
    textAlign: "center",
    fontWeight: "600",
    fontSize: "13px"
  },

  matchButton: {
    padding: "10px",
    background: "#1f3a5f",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    width: "220px"
  },

  errorBox: {
    background: "#fdecea",
    padding: "10px",
    borderRadius: "4px",
    color: "#c62828",
    fontSize: "13px"
  },

  successBox: {
    background: "#edf7ed",
    color: "#2e7d32",
    padding: "10px",
    borderRadius: "4px",
    fontSize: "13px"
  },

  preview: {
    marginTop: "10px"
  },

  sectionTitle: {
    color: "#1e293b",
    marginBottom: "8px",
    fontSize: "14px",
    fontWeight: "600"
  },

  table: {
    width: "100%",
    borderCollapse: "collapse"
  },

  row: {
    borderBottom: "1px solid #e5e7eb"
  },

  cell: {
    padding: "10px",
    color: "#1e293b",
    fontSize: "13px",
    verticalAlign: "middle"
  },

  fileName: {
    maxWidth: "240px",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis"
  },

  statusBadge: {
    padding: "4px 10px",
    borderRadius: "12px",
    background: "#4a6fa5",
    color: "#fff",
    fontSize: "11px",
    fontWeight: "600"
  },

  errorText: {
    color: "#c62828",
    fontSize: "12px"
  },

  submitButton: {
    marginTop: "12px",
    padding: "12px",
    background: "#1f3a5f",
    color: "#fff",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    width: "260px"
  },

  progressWrapper: {
    display: "flex",
    alignItems: "center",
    gap: "6px"
  },

  progressBarContainer: {
    width: "100px",
    height: "6px",
    background: "#e5e7eb",
    borderRadius: "4px",
    overflow: "hidden"
  },

  progressBarFill: {
    height: "100%",
    background: "#4a6fa5",
    transition: "width 0.3s ease"
  },

  progressText: {
    fontSize: "11px",
    color: "#6b7280"
  }
};
export default BulkIngestionDashboard;