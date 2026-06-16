import React, { useState } from "react";
import logo from "../../assets/nemhem-logo.svg";

function Login({ onLogin, onSwitchSignup }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async () => {
    setError("");

    if (!username || !password) {
      setError("Username and password are required");
      return;
    }

    try {
      setLoading(true);

      const res = await fetch("http://localhost:8000/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ username, password })
      });

      const data = await res.json();

      if (res.ok) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role);
        onLogin();
      } else {
        setError(data.detail || "Login failed");
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
            <h2 style={styles.title}>Welcome Back</h2>
            <p style={styles.subtitle}>Please sign in to your account</p>
          </div>

          <input
            style={styles.input}
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <input
            type="password"
            style={styles.input}
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <p style={styles.error}>{error}</p>}

          <button
            style={{
              ...styles.button,
              ...(loading ? styles.buttonDisabled : {})
            }}
            onClick={handleLogin}
            disabled={loading}
          >
            {loading ? <span style={styles.loader}></span> : "Sign In"}
          </button>

          <p style={styles.switchText}>
            Don't have an account?{" "}
            <span onClick={onSwitchSignup} style={styles.link}>
              Sign up
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
    maxWidth: "420px",
    padding: "48px",
    display: "flex",
    flexDirection: "column",
    gap: "24px"
  },

  formHeader: {
    marginBottom: "16px"
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

  input: {
    padding: "16px",
    borderRadius: "12px",
    border: "1.5px solid #e2e8f0",
    background: "#f8fafc",
    color: "#0f172a",
    fontSize: "15px",
    transition: "all 0.2s ease",
    outline: "none"
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
    marginTop: "8px"
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
    border: "1px solid #fee2e2"
  },

  switchText: {
    textAlign: "center",
    marginTop: "24px",
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

export default Login;