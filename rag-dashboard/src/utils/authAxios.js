// rag-dashboard/src/utils/authAxios.js

import axios from "axios";

const authAxios = axios.create({
  baseURL: "http://127.0.0.1:8000"
});

/**
 * 🔐 Attach token to every request
 */
authAxios.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

/**
 * 🚨 Handle token expiry / invalid token
 */
authAxios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401 && !error.config.url.includes("/docs")) {
      console.warn("Session expired. Logging out...");

      // 🔥 Show message to user
      alert("Session expired. Please login again.");

      // 🔥 Clear session
      localStorage.removeItem("token");
      localStorage.removeItem("role");

      // 🔥 Redirect to login
      window.location.href = "/";
    }

    return Promise.reject(error);
  }
);

export default authAxios;