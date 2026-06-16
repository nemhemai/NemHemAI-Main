/**rag-dashboard/src/components/JobDashboard.js */

import React, { useEffect, useState, useMemo } from "react";
import axios from "axios";
import StatusTracker from "./StatusTracker";

/**
 * JobDashboard (Advanced)
 * ----------------------------------------
 * Features:
 * - Shows job title instead of ID
 * - Status badges (LIVE from backend)
 * - Retry failed jobs
 * - Persistent local storage
 */
function JobDashboard({ currentJobId, resetTrigger }) {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobStatuses, setJobStatuses] = useState({});

  // ✅ SAFE FALLBACK (NO LOGIC CHANGE)
  const safeJobs = useMemo(() => jobs || [], [jobs]);

  /**
   * Load jobs from localStorage
   */
  useEffect(() => {
    const stored = JSON.parse(localStorage.getItem("jobs")) || [];

    /**
     * 🔥 Normalize all jobs into consistent object format
     */
    const normalized = stored
      .map((job) => {
        // old format: string
        if (typeof job === "string") {
          return {
            job_id: job,
            title: "Legacy Job"
          };
        }

        // new format: already correct
        if (job && job.job_id) {
          return job;
        }

        return null;
      })
      .filter(Boolean);

    setJobs(normalized);

    // 🔥 overwrite storage with clean data
    localStorage.setItem("jobs", JSON.stringify(normalized));
  }, []);

  /**
   * Add new job
   */
  useEffect(() => {
    if (!currentJobId) return;

    const newJob = {
      job_id: currentJobId,
      title: "New Document"
    };

    setJobs((prev) => {
      const updated = [newJob, ...prev];
      localStorage.setItem("jobs", JSON.stringify(updated));
      return updated;
    });

    setSelectedJob(currentJobId);
  }, [currentJobId]);

  /**
   * Fetch status for all jobs (light polling)
   */
  useEffect(() => {
    if (safeJobs.length === 0) return;

    const interval = setInterval(async () => {
      const updates = {};

      for (const job of safeJobs) {
        const jobId = job?.job_id;

        if (!jobId) continue; // 🚫 skip invalid safely

        try {
          const res = await axios.get(
            `http://127.0.0.1:8000/api/ingest/status/${jobId}`
          );

          updates[jobId] = res.data.status;

        } catch {
          updates[jobId] = "UNKNOWN";
        }
      }

      setJobStatuses(updates);
    }, 4000);

    return () => clearInterval(interval);
  }, [safeJobs]);

  /**
   * 🔥 RESET DASHBOARD (from App.js)
   */
  useEffect(() => {
    if (resetTrigger) {
      console.log("🔄 Clearing dashboard...");

      // clear state
      setJobs([]);
      setSelectedJob(null);
      setJobStatuses({});

      // clear persisted data
      localStorage.removeItem("jobs");
    }
  }, [resetTrigger]);

  /**
   * Retry logic (re-select job → triggers tracker again)
   */
  const retryJob = (jobId) => {
    setSelectedJob(jobId);
  };

  /**
   * Badge color
   */
  const getStatusColor = (status) => {
    if (status === "COMPLETED") return "#28a745";
    if (status === "FAILED") return "#dc3545";
    if (status === "UNKNOWN") return "#6c757d";
    return "#007bff";
  };

  const getStatusIcon = (status) => {
    if (status === "COMPLETED") return "✔";
    if (status === "FAILED") return "⚠";
    if (status === "LOADING") return "⏳";
    return "●";
  };

  const getProgress = (status) => {
    if (status === "COMPLETED") return "100%";
    if (status === "FAILED") return "100%";
    if (status === "LOADING") return "60%";
    return "30%";
  };

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <h2 style={styles.heading}>Job Dashboard</h2>

        <div style={styles.jobList}>
          {safeJobs.length === 0 && (
            <div style={styles.emptyState}>No jobs yet</div>
          )}

          {safeJobs.map((job) => {
            const jobId = job.job_id;
            const title = job.title;

            if (!jobId) return null;

            const status = jobStatuses[jobId] || "LOADING";

            return (
              <div
                key={jobId}
                style={{
                  ...styles.jobItem,
                  ...(jobId === selectedJob ? styles.activeJob : {})
                }}
                onClick={() => setSelectedJob(jobId)}
              >
                {/* HEADER */}
                <div style={styles.jobHeader}>
                  <div>
                    <div style={styles.title}>{title}</div>
                    <div style={styles.subText}>{jobId}</div>
                  </div>

                  <div style={styles.statusWrapper}>
                    <span style={styles.icon}>
                      {getStatusIcon(status)}
                    </span>

                    <span
                      style={{
                        ...styles.badge,
                        background: getStatusColor(status)
                      }}
                    >
                      {status}
                    </span>
                  </div>
                </div>

                {/* PROGRESS BAR */}
                <div style={styles.progressBar}>
                  <div
                    style={{
                      ...styles.progressFill,
                      width: getProgress(status)
                    }}
                  />
                </div>

                {/* ACTION */}
                {status === "FAILED" && (
                  <button
                    style={styles.retryButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      retryJob(jobId);
                    }}
                  >
                    Retry
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* STATUS VIEW */}
        {selectedJob && (
          <div style={styles.statusBox}>
            <StatusTracker jobId={selectedJob} />
          </div>
        )}
      </div>
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
    color: "#0f172a",
    fontSize: "24px",
    fontWeight: "700",
    margin: "0 0 8px 0"
  },

  jobList: {
    display: "flex",
    flexDirection: "column",
    border: "1px solid #e2e8f0",
    borderRadius: "12px",
    overflow: "hidden",
    background: "#f8fafc"
  },

  jobItem: {
    padding: "16px 20px",
    background: "#fff",
    borderBottom: "1px solid #e2e8f0",
    cursor: "pointer",
    transition: "background 0.2s ease"
  },

  activeJob: {
    background: "#f1f5f9" // subtle selection
  },

  jobHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center"
  },

  title: {
    color: "#0f172a",
    fontWeight: "600",
    fontSize: "15px",
    marginBottom: "4px"
  },

  subText: {
    fontSize: "12px",
    color: "#64748b",
    fontFamily: "monospace"
  },

  statusWrapper: {
    display: "flex",
    alignItems: "center",
    gap: "8px"
  },

  icon: {
    fontSize: "14px"
  },

  badge: {
    color: "#fff",
    padding: "6px 12px",
    borderRadius: "20px",
    fontSize: "12px",
    fontWeight: "600",
    letterSpacing: "0.5px",
    textTransform: "uppercase"
  },

  progressBar: {
    marginTop: "12px",
    height: "6px",
    borderRadius: "6px",
    background: "#e2e8f0",
    overflow: "hidden"
  },

  progressFill: {
    height: "100%",
    background: "linear-gradient(90deg, #003366, #0055a4)",
    transition: "width 0.5s ease-out"
  },

  retryButton: {
    marginTop: "12px",
    padding: "6px 16px",
    borderRadius: "6px",
    border: "1.5px solid #dc2626",
    background: "#fef2f2",
    color: "#dc2626",
    cursor: "pointer",
    fontSize: "13px",
    fontWeight: "600",
    transition: "all 0.2s ease",
    "&:hover": {
      background: "#fee2e2"
    }
  },

  statusBox: {
    marginTop: "16px",
    padding: "20px",
    borderRadius: "12px",
    border: "1px solid #e2e8f0",
    background: "#f8fafc"
  },

  emptyState: {
    textAlign: "center",
    color: "#64748b",
    padding: "32px",
    fontSize: "14px",
    fontWeight: "500"
  }
};

export default JobDashboard;