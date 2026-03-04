import { useState, useContext } from "react";
import API from "../api/client";
import { AuthContext } from "../auth/AuthContext";

export default function FileUpload({ triggerRefresh }) {
  const { user } = useContext(AuthContext);

  const [file, setFile] = useState(null);
  const [domain, setDomain] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const isAdmin = user?.roles?.includes("admin");

  const handleUpload = async () => {
    if (!file) {
      setMessage("Please select a file.");
      return;
    }

    if (isAdmin && !domain) {
      setMessage("Admin must select a domain.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    if (isAdmin) {
      formData.append("file_domain", domain);
    }

    try {
      setLoading(true);
      setMessage("");

      await API.post("/upload/file", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setMessage("File uploaded successfully!");
      setFile(null);
      setDomain("");

      // 🔥 trigger global refresh
      triggerRefresh();

    } catch (error) {
      setMessage(
        error.response?.data?.detail || "Upload failed."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h3>📤 Upload Documents</h3>

      <input
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
        style={styles.fileInput}
      />

      {file && <p style={styles.fileName}>Selected: {file.name}</p>}

      {isAdmin ? (
        <div style={{ marginTop: "10px" }}>
          <label>Domain: </label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          >
            <option value="">-- Select Domain --</option>
            <option value="legal">Legal</option>
            <option value="healthcare">Healthcare</option>
            <option value="finance">Finance</option>
            <option value="academic">Academic</option>
            <option value="business">Business</option>
          </select>
        </div>
      ) : (
        <p style={{ fontSize: "12px", color: "#666" }}>
          Domain will be assigned automatically
          based on your roles.
        </p>
      )}

      <button
        onClick={handleUpload}
        style={styles.uploadBtn}
        disabled={loading}
      >
        {loading ? "Uploading..." : "➕ Upload Document"}
      </button>

      {message && (
        <p style={styles.message}>
          {message}
        </p>
      )}
    </div>
  );
}

const styles = {
  container: {
    border: "1px solid #eee",
    borderRadius: "10px",
    padding: "14px",
  },
  fileInput: {
    marginTop: "4px",
  },
  fileName: {
    fontSize: "13px",
    color: "#444",
    marginTop: "8px",
    marginBottom: "4px",
  },
  uploadBtn: {
    marginTop: "10px",
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    padding: "8px 12px",
    cursor: "pointer",
    fontWeight: 600,
  },
  message: {
    marginTop: "10px",
  },
};