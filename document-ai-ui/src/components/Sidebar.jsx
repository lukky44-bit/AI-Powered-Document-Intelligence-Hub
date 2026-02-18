import { useContext, useEffect, useState } from "react";
import { AuthContext } from "../auth/AuthContext";

export default function Sidebar({ selectedFile, setSelectedFile }) {
  const authContext = useContext(AuthContext);

  if (!authContext) {
    return <div>Error: Auth context not available</div>;
  }

  const { logout } = authContext;
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    const token = localStorage.getItem("token");

    try {
      const response = await fetch(
        "http://localhost:8000/files/my",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (response.ok) {
        setFiles(data.files);
      }
    } catch (error) {
      console.error("Failed to fetch files");
    }
  };

  const handleDelete = async (fileId) => {
    const token = localStorage.getItem("token");

    if (!window.confirm("Are you sure you want to delete this file?"))
      return;

    try {
      setLoading(true);

      const response = await fetch(
        `http://localhost:8000/files/${fileId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        // If deleted file was selected → clear selection
        if (selectedFile === fileId) {
          setSelectedFile(null);
        }

        // Refresh file list
        fetchFiles();
      } else {
        console.error("Failed to delete file");
      }
    } catch (error) {
      console.error("Delete error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h3>📂 My Files</h3>

      {files.length === 0 ? (
        <p style={{ color: "#777" }}>No files uploaded</p>
      ) : (
        files.map((file) => (
          <div
            key={file.file_id}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "6px",
            }}
          >
            <div>
              <input
                type="radio"
                name="selectedFile"
                value={file.file_id}
                checked={selectedFile === file.file_id}
                onChange={() =>
                  setSelectedFile(file.file_id)
                }
              />
              <span style={{ marginLeft: "6px" }}>
                {file.filename}
              </span>
            </div>

            <button
              onClick={() => handleDelete(file.file_id)}
              disabled={loading}
              style={styles.deleteBtn}
            >
              ❌
            </button>
          </div>
        ))
      )}

      <hr />

      <button onClick={logout} style={styles.logout}>
        Logout
      </button>
    </div>
  );
}

const styles = {
  logout: {
    background: "#f44336",
    color: "#fff",
    border: "none",
    padding: "8px 12px",
    cursor: "pointer",
    borderRadius: "4px",
  },
  deleteBtn: {
    background: "transparent",
    border: "none",
    cursor: "pointer",
    fontSize: "14px",
  },
};
