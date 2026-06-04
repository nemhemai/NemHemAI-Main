import React, { useState } from "react";

function Signup() {
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
          <h2 style={styles.title}>Signup</h2>

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
            {loading ? <span style={styles.loader}></span> : "Signup"}
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
    letterSpacing: "0.5px",
    marginBottom: "14px"
  },

  tagline: {
    fontSize: "15px",
    opacity: 0.9,
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
    width: "380px",
    padding: "26px",
    borderRadius: "8px",
    background: "#ffffff",
    border: "1px solid #dcdfe6",
    boxShadow: "0 6px 20px rgba(0,0,0,0.12)",
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },

  title: {
    textAlign: "center",
    fontWeight: "600",
    fontSize: "18px",
    color: "#1e293b"
  },

  formScroll: {
    maxHeight: "280px",
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    paddingRight: "4px"
  },

  input: {
    padding: "12px",
    borderRadius: "6px",
    border: "1px solid #cfd6dd",
    background: "#ffffff",
    color: "#1e293b",
    fontSize: "14px"
  },

  select: {
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
    color: "#fff",
    fontWeight: "600",
    cursor: "pointer",
    boxShadow: "0 2px 6px rgba(0,0,0,0.15)"
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

  success: {
    color: "#2e7d32",
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

export default Signup;