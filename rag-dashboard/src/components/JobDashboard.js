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
        <h2 style={styles.heading}>📂 Job Dashboard</h2>

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
  page: {
    display: "flex",
    justifyContent: "center",
    padding: "30px",
    minHeight: "100vh",
    background: "#f4f6f9" // ✅ removed gradient
  },

  container: {
    width: "900px",
    padding: "25px",
    borderRadius: "8px",
    background: "#ffffff", // ✅ solid card
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

  jobList: {
    display: "flex",
    flexDirection: "column",
    border: "1px solid #e0e0e0",
    borderRadius: "6px",
    overflow: "hidden"
  },

  jobItem: {
    padding: "12px 14px",
    background: "#ffffff",
    borderBottom: "1px solid #e0e0e0",
    cursor: "pointer",
    transition: "background 0.2s ease"
  },

  activeJob: {
    background: "#e8f0fe" // subtle selection (gov style)
  },

  jobHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center"
  },

  title: {
    color: "#1e293b",
    fontWeight: "600",
    fontSize: "14px"
  },

  subText: {
    fontSize: "11px",
    color: "#6b7280"
  },

  statusWrapper: {
    display: "flex",
    alignItems: "center",
    gap: "6px"
  },

  icon: {
    fontSize: "13px"
  },

  badge: {
    color: "#fff",
    padding: "4px 10px",
    borderRadius: "12px",
    fontSize: "11px",
    fontWeight: "600"
  },

  progressBar: {
    marginTop: "8px",
    height: "5px",
    borderRadius: "4px",
    background: "#e5e7eb"
  },

  progressFill: {
    height: "100%",
    background: "#4a6fa5", // muted govt blue
    transition: "width 0.4s ease"
  },

  retryButton: {
    marginTop: "8px",
    padding: "4px 8px",
    borderRadius: "4px",
    border: "1px solid #c62828",
    background: "#fff",
    color: "#c62828",
    cursor: "pointer",
    fontSize: "12px"
  },

  statusBox: {
    marginTop: "10px",
    padding: "12px",
    borderRadius: "6px",
    border: "1px solid #e0e0e0",
    background: "#fafafa"
  },

  emptyState: {
    textAlign: "center",
    color: "#6b7280",
    padding: "16px"
  }
};

export default JobDashboard;