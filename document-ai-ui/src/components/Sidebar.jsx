import { useContext } from "react";
import { AuthContext } from "../auth/AuthContext";

export default function Sidebar() {
  const { logout } = useContext(AuthContext);

  return (
    <div>
      <h3>📂 My Files</h3>

      {/* File list will come next */}
      <p style={{ color: "#777" }}>No files loaded</p>

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
};
