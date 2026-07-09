import React, { useState } from "react";
import authAxios from "../utils/authAxios";

function QueryDashboard() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");

  const handleQuickUpload = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setUploadMessage("Uploading in process...");

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://127.0.0.1:8000/api/ingest/quick-upload", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      const jobs = data.jobs || [];
      
      if (jobs.length > 0) {
        setUploadMessage("Processing document(s)...");
        let allDone = false;
        
        while (!allDone) {
          await new Promise(r => setTimeout(r, 2000)); // Wait 2 seconds between checks
          
          let pendingCount = 0;
          let failedCount = 0;
          
          for (let job of jobs) {
            try {
              const statusRes = await fetch(`http://127.0.0.1:8000/api/ingest/status/${job.job_id}`, {
                headers: { "Authorization": `Bearer ${token}` }
              });
              const statusData = await statusRes.json();
              
              if (statusData.status === "FAILED") failedCount++;
              else if (statusData.status !== "COMPLETED") pendingCount++;
            } catch (e) {
              console.error("Status check error:", e);
            }
          }
          
          if (pendingCount === 0) {
            allDone = true;
            if (failedCount === jobs.length) {
              throw new Error("All ingestion jobs failed");
            } else if (failedCount > 0) {
              setUploadMessage(`Upload Complete (${failedCount} failed)`);
            } else {
              setUploadMessage("Upload Complete");
            }
          }
        }
      } else {
        setUploadMessage("Upload Complete");
      }
      
      setTimeout(() => setUploadMessage(""), 5000);
    } catch (err) {
      console.error(err);
      setUploadMessage("Failed to upload document(s)");
      setTimeout(() => setUploadMessage(""), 5000);
    } finally {
      setIsUploading(false);
      event.target.value = null; // reset input
    }
  };

  const handleSubmit = async () => {
    if (!query.trim()) {
      setError("Query cannot be empty");
      return;
    }

    setLoading(true);
    setIsGenerating(false);
    setError("");
    setResult({ answer_original: "", citations: [], confidence: "" }); // Initialize empty result for streaming

    try {
      // Get token from localStorage to authenticate fetch
      const token = localStorage.getItem("token");
      const response = await fetch("http://127.0.0.1:8000/api/v1/query/query/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;
      let streamedText = "";
      let metadataSet = false;

      // We no longer need the loading spinner for generating because it streams instantly
      setLoading(false);
      setIsGenerating(true);

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;

        if (value) {
          const chunkString = decoder.decode(value, { stream: true });
          
          // The backend yields JSON strings separated by \n
          const parts = chunkString.split("\n");
          for (let part of parts) {
            if (!part.trim()) continue;
            
            try {
              const parsed = JSON.parse(part);
              
              if (parsed.type === "metadata") {
                setResult(prev => ({
                  ...prev,
                  citations: parsed.citations || [],
                  confidence: parsed.confidence || ""
                }));
                metadataSet = true;
              } else if (parsed.type === "chunk") {
                streamedText += parsed.content;
                setResult(prev => ({
                  ...prev,
                  answer_original: streamedText
                }));
              } else if (parsed.type === "error") {
                setError(parsed.content);
              }
            } catch (e) {
              console.warn("Failed to parse chunk:", part, e);
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      setError(err.message || "Query failed");
    } finally {
      setLoading(false);
      setIsGenerating(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.container}>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={styles.heading}>🔍 Query Dashboard</h2>
          {uploadMessage && (
            <div style={{
              background: uploadMessage.includes("Failed") ? "#fee2e2" : "#ecfdf5",
              color: uploadMessage.includes("Failed") ? "#b91c1c" : "#047857",
              padding: "6px 16px",
              borderRadius: "20px",
              fontSize: "13px",
              fontWeight: "500",
              border: uploadMessage.includes("Failed") ? "1px solid #fca5a5" : "1px solid #a7f3d0",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
            }}>
              {isUploading ? <span style={{ display: "inline-block", animation: "spin 2s linear infinite" }}>⏳</span> : "✅"} 
              {uploadMessage}
            </div>
          )}
        </div>

        <div style={styles.layout}>

          {/* LEFT PANEL */}
          <div style={styles.leftPanel}>

            {/* SEARCH */}
            <div style={styles.searchCard}>
              <label style={{ cursor: "pointer", display: "flex", alignItems: "center", padding: "0 10px", color: "#6b7280" }} title="Attach PDF documents">
                <input 
                  type="file" 
                  multiple 
                  accept="application/pdf" 
                  style={{ display: "none" }} 
                  onChange={handleQuickUpload}
                  disabled={isUploading}
                />
                📎
              </label>
              
              <input
                style={styles.input}
                placeholder="Ask a question about documents..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSubmit();
                }}
              />

              <button onClick={handleSubmit} style={styles.button}>
                {loading ? "Searching..." : "Search"}
              </button>
            </div>

            {/* ERROR */}
            {error && <div style={styles.errorBox}>⚠ {error}</div>}

            {/* LOADING */}
            {loading && (
              <div style={styles.loadingBox}>
                🔍 Retrieving documents... <br />
                🧠 Generating answer...
              </div>
            )}

            {/* ANSWER */}
            {result && (
              <div style={styles.answerCard}>
                <h3>📄 Answer</h3>

                <p style={styles.answerHint}>
                  Extracted from verified documents
                </p>

                <p style={styles.answerText}>
                  {result.answer_original ? (
                    result.answer_original
                  ) : (
                    <span style={{ color: "#6b7280", fontStyle: "italic", display: "inline-block", animation: "pulse 1.5s infinite" }}>
                      ⏳ Analyzing context and generating answer...
                    </span>
                  )}
                </p>

                <div style={styles.confidence}>
                  Confidence:
                  <span style={styles.confidenceBadge}>
                    {result.confidence}
                  </span>
                </div>
              </div>
            )}

          </div>

          {/* RIGHT PANEL */}
          <div style={styles.rightPanel}>
            <div style={styles.citationsCard}>
              <h3>📚 Supporting Evidence</h3>

              {!result && !loading && !isGenerating && (
                <p style={styles.noData}>
                  Your citations will appear here
                </p>
              )}

              {isGenerating && (
                <div style={{ padding: "20px", textAlign: "center", color: "#6b7280" }}>
                   <span style={{ display: "inline-block", animation: "pulse 1.5s infinite", fontSize: "24px" }}>⏳</span>
                   <p style={{ marginTop: "10px", fontSize: "13px" }}>Collating and verifying sources...</p>
                </div>
              )}

              {result && !isGenerating &&
                result.citations.map((c, idx) => {
                  console.log("CITATION OBJECT:", c);

                  return (
                  <div key={idx} style={styles.citationItem}>
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: "inline-block",
                        color: "#1f3a5f",
                        fontWeight: "600",
                        textDecoration: "underline",
                        cursor: "pointer"
                      }}
                    >
                      📄 {c.document_name} (Page {c.page})
                    </a>

                    <p style={styles.snippet}>
                      {(c.snippet || "").slice(0, 180)}...
                    </p>
                  </div>
                );
           })}
            </div>
          </div>

        </div>
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
    maxWidth: "1100px",
    width: "100%",
    padding: "25px",
    borderRadius: "8px",
    background: "#ffffff",
    border: "1px solid #dcdfe6",
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
    boxSizing: "border-box"
  },

  heading: {
    color: "#1e293b",
    fontSize: "20px",
    fontWeight: "600"
  },

  layout: {
    display: "flex",
    gap: "16px"
  },

  leftPanel: {
    flex: 2,
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },

  rightPanel: {
    flex: 1
  },

  searchCard: {
    display: "flex",
    gap: "8px",
    padding: "12px",
    borderRadius: "6px",
    background: "#f9fafb",
    border: "1px solid #e5e7eb"
  },

  input: {
    flex: 1,
    padding: "10px",
    borderRadius: "6px",
    border: "1px solid #cfd6dd",
    background: "#ffffff",
    color: "#1e293b",
    fontSize: "14px"
  },

  button: {
    padding: "10px 16px",
    borderRadius: "4px",
    border: "none",
    background: "#1f3a5f",
    color: "#fff",
    fontWeight: "600",
    cursor: "pointer"
  },

  errorBox: {
    background: "#fdecea",
    padding: "10px",
    borderRadius: "4px",
    color: "#c62828",
    fontSize: "13px"
  },

  loadingBox: {
    background: "#f1f5f9",
    padding: "12px",
    borderRadius: "4px",
    color: "#374151",
    fontSize: "13px"
  },

  answerCard: {
    padding: "14px",
    borderRadius: "6px",
    background: "#ffffff",
    border: "1px solid #e5e7eb"
  },

  answerText: {
    fontSize: "14px",
    lineHeight: "1.6",
    color: "#1e293b"
  },

  answerHint: {
    fontSize: "12px",
    color: "#6b7280",
    marginBottom: "6px"
  },

  confidence: {
    marginTop: "8px",
    fontSize: "13px",
    color: "#374151"
  },

  confidenceBadge: {
    marginLeft: "6px",
    padding: "3px 8px",
    background: "#e5e7eb",
    borderRadius: "6px",
    fontSize: "11px",
    color: "#1e293b"
  },

  citationsCard: {
    padding: "14px",
    borderRadius: "6px",
    background: "#ffffff",
    border: "1px solid #e5e7eb",
    position: "relative",
    zIndex: 1,
    pointerEvents: "auto"
  },

  citationItem: {
    marginTop: "10px",
    padding: "10px",
    borderRadius: "4px",
    background: "#f9fafb",
    border: "1px solid #e5e7eb",
    pointerEvents: "auto",   // 🔥 FIX
    position: "relative",
    zIndex: 10               // 🔥 FIX
  },

  citationHeader: {
    marginBottom: "4px",
    fontSize: "12px"
  },

  docName: {
    color: "#1f3a5f",
    fontWeight: "600"
  },

  pageText: {
    color: "#6b7280"
  },

  snippet: {
    fontSize: "12px",
    color: "#374151"
  },

  noData: {
    color: "#6b7280",
    fontSize: "13px"
  },

  docLink: {
    display: "inline-block",
    color: "#1f3a5f",
    fontWeight: "600",
    textDecoration: "underline",
    cursor: "pointer"
  }

};

export default QueryDashboard;