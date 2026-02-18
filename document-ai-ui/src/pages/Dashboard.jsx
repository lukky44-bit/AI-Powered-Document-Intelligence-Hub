import { useState } from "react";
import { jwtDecode } from "jwt-decode";
import Sidebar from "../components/Sidebar";
import FileUpload from "../components/FileUpload";
import RagQuery from "../components/RagQuery";
import AdminPanel from "../components/AdminPanel";

export default function Dashboard() {
  const [selectedFile, setSelectedFile] = useState(null);

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

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      
      {/* Sidebar */}
      <div
        style={{
          width: "250px",
          padding: "20px",
          borderRight: "1px solid #ddd",
          background: "#f9f9f9",
        }}
      >
        <Sidebar
          selectedFile={selectedFile}
          setSelectedFile={setSelectedFile}
        />
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: "30px", overflowY: "auto" }}>
        
        <FileUpload />

        {/* Admin-only Role Management */}
        {isAdmin && <AdminPanel />}

        <div style={{ marginTop: "40px" }}>
          <RagQuery selectedFile={selectedFile} />
        </div>

      </div>
    </div>
  );
}
