import React, { useState } from "react";
import logo from "../../assets/nemhem-logo.svg";

function Signup({ onSwitchLogin }) {
  const [form, setForm] = useState({
    username: "",
    password: "",
    role: "viewer",
    full_name: "",
    email: "",
    department: "",
    designation: ""
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSignup = async () => {
    setError("");
    setMessage("");

    if (!form.username || !form.password) {
      setError("Username and password are required");
      return;
    }

    if (form.password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    try {
      setLoading(true);

      const res = await fetch("http://localhost:8000/api/auth/signup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(form)
      });

      const data = await res.json();

      if (res.ok) {
        setMessage("Signup successful. Please login.");
      } else {
        setError(data.detail || "Signup failed");
      }

    } catch {
      setError("Server error. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>

      {/* LEFT PANEL */}
      <div style={styles.leftPanel}>
        <div style={styles.brandContainer}>
          <img src={logo} alt="NemhemAI Logo" style={styles.logoLarge} />
          <h1 style={styles.brandTitle}>NemhemAI</h1>
          <div style={styles.divider}></div>
          <h2 style={styles.brandSubtitle}>Government RAG System</h2>
          <p style={styles.tagline}>
            Secure document processing and intelligent retrieval platform
          </p>
        </div>
        <div style={styles.meshGradient}></div>
      </div>

      {/* RIGHT PANEL */}
      <div style={styles.rightPanel}>
        <div style={styles.container}>
          <div style={styles.formHeader}>
            <h2 style={styles.title}>Create Account</h2>
            <p style={styles.subtitle}>Register for secure platform access</p>
          </div>

          <div style={styles.formScroll}>

            <input name="username" placeholder="Username" value={form.username} onChange={handleChange} style={styles.input} />
            <input name="password" type="password" placeholder="Password" value={form.password} onChange={handleChange} style={styles.input} />

            <input name="full_name" placeholder="Full Name" value={form.full_name} onChange={handleChange} style={styles.input} />
            <input name="email" placeholder="Email" value={form.email} onChange={handleChange} style={styles.input} />

            <input name="department" placeholder="Department" value={form.department} onChange={handleChange} style={styles.input} />
            <input name="designation" placeholder="Designation" value={form.designation} onChange={handleChange} style={styles.input} />

            <select name="role" value={form.role} onChange={handleChange} style={styles.select}>
              <option value="admin">Admin</option>
              <option value="officer">Officer</option>
              <option value="viewer">Viewer</option>
            </select>

          </div>

          {error && <p style={styles.error}>{error}</p>}
          {message && <p style={styles.success}>{message}</p>}

          <button
            style={{
              ...styles.button,
              ...(loading ? styles.buttonDisabled : {})
            }}
            onClick={handleSignup}
            disabled={loading}
          >
            {loading ? <span style={styles.loader}></span> : "Sign Up"}
          </button>

          <p style={styles.switchText}>
            Already have an account?{" "}
            <span onClick={onSwitchLogin} style={styles.link}>
              Sign in
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    display: "flex",
    height: "100vh",
    width: "100vw",
    fontFamily: "'Inter', 'Segoe UI', sans-serif",
    background: "#f4f7fb"
  },

  leftPanel: {
    width: "55%",
    background: "linear-gradient(135deg, #001f3f 0%, #003366 100%)",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "80px",
    position: "relative",
    overflow: "hidden"
  },

  meshGradient: {
    position: "absolute",
    top: "-50%",
    left: "-50%",
    width: "200%",
    height: "200%",
    background: "radial-gradient(circle at 50% 50%, rgba(255,255,255,0.05) 0%, transparent 60%)",
    pointerEvents: "none"
  },

  brandContainer: {
    zIndex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    maxWidth: "500px"
  },

  logoLarge: {
    width: "72px",
    height: "72px",
    marginBottom: "24px",
    filter: "drop-shadow(0px 4px 8px rgba(0,0,0,0.2))"
  },

  brandTitle: {
    fontSize: "48px",
    fontWeight: "800",
    letterSpacing: "1px",
    margin: "0 0 16px 0",
    background: "linear-gradient(to right, #ffffff, #b3d4ff)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent"
  },

  divider: {
    width: "60px",
    height: "4px",
    background: "#00a8ff",
    marginBottom: "24px",
    borderRadius: "2px"
  },

  brandSubtitle: {
    fontSize: "28px",
    fontWeight: "600",
    margin: "0 0 16px 0",
    color: "#e6f0ff"
  },

  tagline: {
    fontSize: "16px",
    color: "#b3d4ff",
    lineHeight: "1.7",
    margin: 0
  },

  rightPanel: {
    width: "45%",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    background: "#ffffff"
  },

  container: {
    width: "100%",
    maxWidth: "460px",
    padding: "48px",
    display: "flex",
    flexDirection: "column",
    gap: "24px"
  },

  formHeader: {
    marginBottom: "8px"
  },

  title: {
    fontWeight: "700",
    fontSize: "32px",
    color: "#001f3f",
    margin: "0 0 8px 0"
  },

  subtitle: {
    fontSize: "15px",
    color: "#64748b",
    margin: 0
  },

  formScroll: {
    maxHeight: "340px",
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
    paddingRight: "8px",
    "&::-webkit-scrollbar": {
      width: "6px"
    },
    "&::-webkit-scrollbar-thumb": {
      background: "#cbd5e1",
      borderRadius: "4px"
    }
  },

  input: {
    padding: "16px",
    borderRadius: "12px",
    border: "1.5px solid #e2e8f0",
    background: "#f8fafc",
    color: "#0f172a",
    fontSize: "15px",
    transition: "all 0.2s ease",
    outline: "none",
    width: "100%",
    boxSizing: "border-box"
  },

  select: {
    padding: "16px",
    borderRadius: "12px",
    border: "1.5px solid #e2e8f0",
    background: "#f8fafc",
    color: "#0f172a",
    fontSize: "15px",
    transition: "all 0.2s ease",
    outline: "none",
    width: "100%",
    boxSizing: "border-box"
  },

  button: {
    padding: "16px",
    borderRadius: "12px",
    border: "none",
    background: "#003366",
    color: "#fff",
    fontSize: "16px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.2s ease",
    boxShadow: "0 4px 12px rgba(0, 51, 102, 0.2)",
    marginTop: "8px",
    width: "100%"
  },

  buttonDisabled: {
    opacity: 0.7,
    cursor: "not-allowed"
  },

  error: {
    color: "#ef4444",
    fontSize: "14px",
    textAlign: "center",
    background: "#fef2f2",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #fee2e2",
    margin: 0
  },

  success: {
    color: "#15803d",
    fontSize: "14px",
    textAlign: "center",
    background: "#f0fdf4",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #dcfce7",
    margin: 0
  },

  switchText: {
    textAlign: "center",
    marginTop: "16px",
    color: "#64748b",
    fontSize: "14px"
  },

  link: {
    color: "#0052cc",
    fontWeight: "600",
    cursor: "pointer",
    textDecoration: "none"
  },

  loader: {
    width: "20px",
    height: "20px",
    border: "2px solid #fff",
    borderTop: "2px solid transparent",
    borderRadius: "50%",
    display: "inline-block",
    animation: "spin 0.8s linear infinite"
  }
};

export default Signup;