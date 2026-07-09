import React, { useState } from "react";
import authAxios from "../utils/authAxios";

function QueryDashboard() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    if (!query.trim()) {
      setError("Query cannot be empty");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await authAxios.post("/api/v1/query/query", { query });
      setResult(res.data);
    } catch (err) {
      const msg = err.response?.data?.detail || "Query failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.container}>

        <h2 style={styles.heading}>🔍 Query Dashboard</h2>

        <div style={styles.layout}>

          {/* LEFT PANEL */}
          <div style={styles.leftPanel}>

            {/* SEARCH */}
            <div style={styles.searchCard}>
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
                  {result.answer_original}
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

              {!result && (
                <p style={styles.noData}>
                  Your citations will appear here
                </p>
              )}

              {result &&
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