import React, { useState } from "react";

function Login({ onLogin }) {
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
        <div>
          <h1 style={styles.brand}>Government RAG System</h1>
          <p style={styles.tagline}>
            Secure document processing and intelligent retrieval platform
          </p>
        </div>
      </div>

      {/* RIGHT PANEL */}
      <div style={styles.rightPanel}>
        <div style={styles.container}>
          <h2 style={styles.title}>Login</h2>

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
            {loading ? <span style={styles.loader}></span> : "Login"}
          </button>
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
    fontFamily: "Segoe UI, sans-serif",
    background: "#f4f6f9"
  },

  leftPanel: {
    width: "50%",
    background: "#1f3a5f",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "80px"
  },

  brand: {
    fontSize: "44px",
    fontWeight: "700",
    letterSpacing: "0.5px"
  },

  tagline: {
    fontSize: "15px",
    opacity: 0.85,
    maxWidth: "420px",
    lineHeight: "1.6"
  },

  rightPanel: {
    width: "50%",
    display: "flex",
    justifyContent: "center",
    alignItems: "center"
  },

  container: {
    width: "360px",
    padding: "28px",
    borderRadius: "8px",
    background: "#ffffff",
    border: "1px solid #dcdfe6",
    boxShadow: "0 6px 20px rgba(0,0,0,0.12)",
    display: "flex",
    flexDirection: "column",
    gap: "14px"
  },

  title: {
    textAlign: "center",
    fontWeight: "600",
    fontSize: "18px",
    color: "#1e293b"
  },

  input: {
    padding: "12px",
    borderRadius: "6px",
    border: "1px solid #cfd6dd",
    background: "#ffffff",
    color: "#1e293b",
    fontSize: "14px"
  },

  button: {
    padding: "12px",
    borderRadius: "6px",
    border: "none",
    background: "#1f3a5f",
    boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
    color: "#fff",
    fontWeight: "600",
    cursor: "pointer"
  },

  buttonDisabled: {
    opacity: 0.7,
    cursor: "not-allowed"
  },

  error: {
    color: "#c62828",
    fontSize: "13px",
    textAlign: "center"
  },

  loader: {
    width: "16px",
    height: "16px",
    border: "2px solid #fff",
    borderTop: "2px solid transparent",
    borderRadius: "50%",
    display: "inline-block",
    animation: "spin 0.8s linear infinite"
  }
};

export default Login;