/** rag-dashboard/src/components/StatusTracker.js */

import React, { useEffect, useState } from "react";
import authAxios from "../utils/authAxios";

/**
 * Ordered pipeline stages
 */
const statusSteps = [
  "UPLOADED",
  "REGISTERED",
  "EXTRACTING",
  "VALIDATING",
  "STORING_ELEMENTS",
  "CHUNKING",
  "EMBEDDING",
  "COMPLETED"
];

function StatusTracker({ jobId }) {
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (!jobId) return;

    let interval;

    interval = setInterval(async () => {
      try {
        const res = await authAxios.get(`/api/ingest/status/${jobId}`);
        
        const data = res.data;

        setStatus(data.status);
        setProgress(data.progress || 0);
        setError(data.error || "");
        setRetryCount(0);

        if (data.status === "COMPLETED" || data.status === "FAILED") {
          clearInterval(interval);
        }

      } catch (err) {
        console.log("Polling error:", err.message);

        setRetryCount((prev) => {
          const next = prev + 1;

          if (next >= 5) {
            clearInterval(interval);
            setError("Server not responding.");
          }

          return next;
        });
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId]);

  /**
   * Determine step state
   */
  const getStepState = (step, index) => {
    const currentIndex = statusSteps.indexOf(status);

    if (status === "FAILED") {
      if (index === currentIndex) return "failed";
      if (index < currentIndex) return "completed";
      return "pending";
    }

    if (index < currentIndex) return "completed";
    if (index === currentIndex) return "active";
    return "pending";
  };

  /**
   * Icon based on state
   */
  const getIcon = (state) => {
    if (state === "completed") return "✔";
    if (state === "active") return "⏳";
    if (state === "failed") return "❌";
    return "•";
  };

  /**
   * Color based on state
   */
  const getColor = (state) => {
    if (state === "completed") return "#28a745";
    if (state === "active") return "#007bff";
    if (state === "failed") return "#dc3545";
    return "#aaa";
  };

  return (
    <div style={styles.container}>
      <h3 style={styles.heading}>📊 Pipeline Execution</h3>

      {/* PROGRESS */}
      <div style={styles.progressWrapper}>
        <div style={styles.progressBarBg}>
          <div
            style={{
              ...styles.progressBarFill,
              width: `${progress}%`,
              background:
                status === "FAILED"
                  ? "#dc3545"
                  : status === "COMPLETED"
                  ? "#28a745"
                  : "#667eea"
            }}
          />
        </div>
        <span style={styles.progressText}>{progress}%</span>
      </div>

      {/* STATUS */}
      <div style={styles.statusRow}>
        <span style={styles.label}>Status:</span>
        <span
          style={{
            ...styles.badge,
            background:
              status === "FAILED"
                ? "#dc3545"
                : status === "COMPLETED"
                ? "#28a745"
                : "#667eea"
          }}
        >
          {getIcon(getStepState(status, statusSteps.indexOf(status)))} {status || "INITIALIZING"}
        </span>
      </div>

      {/* ERROR */}
      {error && <div style={styles.errorBox}>⚠ {error}</div>}

      {/* STEPS */}
      <div style={styles.steps}>
        {statusSteps.map((step, index) => {
          const state = getStepState(step, index);

          return (
            <div
              key={step}
              style={{
                ...styles.stepCard,
                ...(state === "active" ? styles.activeStep : {}),
                ...(state === "completed" ? styles.completedStep : {}),
                ...(state === "failed" ? styles.failedStep : {})
              }}
            >
              <div style={styles.stepLeft}>
                <div
                  style={{
                    ...styles.stepIcon,
                    background: getColor(state)
                  }}
                >
                  {getIcon(state)}
                </div>

                {index !== statusSteps.length - 1 && (
                  <div style={styles.stepLine} />
                )}
              </div>

              <div style={styles.stepContent}>
                <span style={styles.stepText}>{step}</span>
                <span style={styles.stepState}>{state}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

}

/**
 * Styles
 */
const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
    padding: "16px",
    borderRadius: "6px",
    background: "#ffffff",
    border: "1px solid #e0e0e0"
  },

  heading: {
    color: "#1e293b",
    fontSize: "16px",
    fontWeight: "600"
  },

  progressWrapper: {
    display: "flex",
    alignItems: "center",
    gap: "10px"
  },

  progressBarBg: {
    flex: 1,
    height: "8px",
    borderRadius: "4px",
    background: "#e5e7eb",
    overflow: "hidden"
  },

  progressBarFill: {
    height: "100%",
    borderRadius: "4px",
    transition: "width 0.3s ease",
    background: "#4a6fa5" // muted govt blue
  },

  progressText: {
    color: "#374151",
    fontSize: "12px"
  },

  statusRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px"
  },

  label: {
    color: "#374151",
    fontWeight: "500",
    fontSize: "13px"
  },

  badge: {
    color: "#fff",
    padding: "4px 10px",
    borderRadius: "12px",
    fontSize: "11px",
    fontWeight: "600"
  },

  errorBox: {
    background: "#fdecea",
    color: "#c62828",
    padding: "8px",
    borderRadius: "4px",
    fontSize: "13px"
  },

  steps: {
    display: "flex",
    flexDirection: "column",
    gap: "8px"
  },

  stepCard: {
    display: "flex",
    gap: "10px",
    padding: "10px",
    borderRadius: "4px",
    background: "#ffffff",
    border: "1px solid #e0e0e0"
  },

  activeStep: {
    background: "#e8f0fe",
    border: "1px solid #4a6fa5"
  },

  completedStep: {
    background: "#f1f8f4",
    border: "1px solid #2e7d32"
  },

  failedStep: {
    background: "#fdecea",
    border: "1px solid #c62828"
  },

  stepLeft: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center"
  },

  stepIcon: {
    width: "20px",
    height: "20px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#fff",
    fontSize: "11px"
  },

  stepLine: {
    width: "2px",
    flex: 1,
    background: "#d1d5db",
    marginTop: "4px"
  },

  stepContent: {
    display: "flex",
    flexDirection: "column"
  },

  stepText: {
    color: "#1e293b",
    fontWeight: "600",
    fontSize: "13px"
  },

  stepState: {
    fontSize: "11px",
    color: "#6b7280"
  }
};

export default StatusTracker;