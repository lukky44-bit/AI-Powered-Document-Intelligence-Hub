import { useEffect, useState } from "react";
import API from "../api/client";

export default function FileList({ refreshTrigger }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadFiles = async () => {
    try {
      setLoading(true);
      const response = await API.get("/files/my");
      setFiles(response.data.files);
    } catch (err) {
      console.error("Failed to load files");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, [refreshTrigger]);

  const handleDelete = async (fileId) => {
    if (!window.confirm("Delete this file?")) return;

    try {
      await API.delete(`/files/${fileId}`);
      loadFiles();
    } catch (err) {
      alert("Failed to delete file");
    }
  };

  return (
    <div style={{ marginTop: "20px" }}>
      <h4>📁 Your Files</h4>

      {loading && <p>Loading...</p>}

      {files.length === 0 && !loading && (
        <p style={{ fontSize: "13px", color: "#777" }}>
          No files uploaded yet.
        </p>
      )}

      {files.map((file) => (
        <div
          key={file.file_id}
          style={styles.fileItem}
        >
          <span>{file.filename}</span>

          <button
            onClick={() =>
              handleDelete(file.file_id)
            }
            style={styles.deleteBtn}
          >
            Delete
          </button>
        </div>
      ))}
    </div>
  );
}

const styles = {
  fileItem: {
    display: "flex",
    justifyContent: "space-between",
    padding: "6px 0",
    borderBottom: "1px solid #eee",
  },
  deleteBtn: {
    background: "#ff4d4f",
    border: "none",
    color: "#fff",
    padding: "4px 8px",
    borderRadius: "4px",
    cursor: "pointer",
  },
};