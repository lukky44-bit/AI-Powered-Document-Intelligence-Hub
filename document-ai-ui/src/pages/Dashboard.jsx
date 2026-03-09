import { useContext, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";
import { AuthContext } from "../auth/AuthContext";

export default function Dashboard() {
  const [fileRefreshKey, setFileRefreshKey] = useState(0);
  const { chatId } = useParams();
  const navigate = useNavigate();

  const activeChat = chatId || null;

  const { user, logout } = useContext(AuthContext);

  const triggerFileRefresh = () => {
    setFileRefreshKey((prev) => prev + 1);
  };

  const handleSelectChat = (id) => {
    navigate(`/chats/${id}/message`);
  };

  const handleCreateChat = (id) => {
    navigate(`/chats/${id}/message`);
  };

  return (
    <div style={styles.container}>
      <div style={styles.sidebar}>
        <Sidebar
          activeChat={activeChat}
          onSelectChat={handleSelectChat}
          onCreateChat={handleCreateChat}
          fileRefreshKey={fileRefreshKey}
        />
      </div>

      <div style={styles.main}>
        <div style={styles.topBar}>
          <div style={styles.userInfo}>
            <strong>{user?.email || "Unknown user"}</strong>
            <span style={styles.roleText}>
              Roles: {user?.roles?.join(", ") || "none"}
            </span>
          </div>
          <button onClick={logout} style={styles.logoutBtn}>
            Logout
          </button>
        </div>

        <ChatWindow
          activeChat={activeChat}
          fileRefreshKey={fileRefreshKey}
          onUploadSuccess={triggerFileRefresh}
        />
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    height: "100vh",
  },
  sidebar: {
    width: "280px",
    borderRight: "1px solid #ddd",
    padding: "16px",
  },
  main: {
    flex: 1,
    padding: "16px",
    display: "flex",
    flexDirection: "column",
    gap: "20px",
    overflowY: "auto",
  },
  topBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "1px solid #eee",
    paddingBottom: "8px",
  },
  userInfo: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  },
  roleText: {
    fontSize: "12px",
    color: "#666",
  },
  logoutBtn: {
    background: "#ff4d4f",
    color: "#fff",
    border: "none",
    borderRadius: "6px",
    padding: "8px 12px",
    cursor: "pointer",
  },
};