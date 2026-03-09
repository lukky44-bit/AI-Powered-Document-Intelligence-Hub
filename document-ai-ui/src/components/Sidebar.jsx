import { useEffect, useState } from "react";
import { createChat, fetchChats } from "../api/chat";
import AdminPanel from "./AdminPanel";
import FileList from "./FileList";

export default function Sidebar({
  activeChat,
  onSelectChat,
  onCreateChat,
  fileRefreshKey,
}) {
  const [chats, setChats] = useState([]);

  const loadChats = async () => {
    const data = await fetchChats();
    setChats(data);
  };

  useEffect(() => {
    loadChats();
  }, []);

  const handleNewChat = async () => {
    const data = await createChat();
    onCreateChat(data.chat_id);
    loadChats();
  };

  return (
    <div>
      <h3>💬 Chats</h3>

      <button onClick={handleNewChat} style={styles.newChat}>
        ➕ New Chat
      </button>

      <ul style={styles.list}>
        {chats.map((chat) => (
          <li
            key={chat.chat_id}
            onClick={() => onSelectChat(chat.chat_id)}
            style={{
              ...styles.item,
              background: activeChat === chat.chat_id ? "#eee" : "transparent",
            }}
          >
            {chat.title}
          </li>
        ))}
      </ul>

      <div style={styles.adminSection}>
        <AdminPanel />
      </div>

      <div style={styles.filesSection}>
        <FileList refreshTrigger={fileRefreshKey} />
      </div>
    </div>
  );
}

const styles = {
  newChat: {
    width: "100%",
    marginBottom: "10px",
  },
  list: {
    listStyle: "none",
    padding: 0,
  },
  item: {
    padding: "8px",
    cursor: "pointer",
    borderRadius: "4px",
    marginBottom: "4px",
  },
  adminSection: {
    marginTop: "14px",
    paddingTop: "10px",
    borderTop: "1px solid #eee",
  },
  filesSection: {
    marginTop: "14px",
    paddingTop: "10px",
    borderTop: "1px solid #eee",
  },
};