import { useState } from "react";
import { jwtDecode } from "jwt-decode";

export default function FileUpload() {
  const [file, setFile] = useState(null);
  const [domain, setDomain] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const token = localStorage.getItem("token");

  // Decode roles
  let roles = [];
  if (token) {
    try {
      const decoded = jwtDecode(token);
      roles = decoded.roles || [];
    } catch (err) {
      console.error("Invalid token");
    }
  }

  const isAdmin = roles.includes("admin");

  const handleUpload = async () => {
    if (!file) {
      setMessage("Please select a file.");
      return;
    }

    // 🔥 Admin must select domain
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

      const response = await fetch("http://localhost:8000/upload/file", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setMessage("File uploaded successfully!");
        setFile(null);
        setDomain(""); // reset domain after upload
      } else {
        setMessage(data.detail || "Upload failed.");
      }
    } catch (error) {
      setMessage("Server error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h3>📤 Upload Documents</h3>

      <input
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
      />

      {/* Admin-only domain selection */}
      {isAdmin && (
        <div style={{ marginTop: "10px" }}>
          <label style={{ marginRight: "8px" }}>Domain:</label>

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
      )}

      <button
        onClick={handleUpload}
        style={{ marginTop: "10px" }}
      >
        {loading ? "Uploading..." : "Upload"}
      </button>

      {message && (
        <p style={{ marginTop: "10px", color: "#555" }}>
          {message}
        </p>
      )}
    </div>
  );
}
