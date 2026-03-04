import { useContext, useEffect, useRef, useState } from "react";
import { fetchMessages, sendMessage } from "../api/chat";
import { fetchMyFiles } from "../api/file";
import API from "../api/client";
import { AuthContext } from "../auth/AuthContext";
import ReactMarkdown from "react-markdown";

export default function ChatWindow({ activeChat, fileRefreshKey, onUploadSuccess }) {
  const { user } = useContext(AuthContext);

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");

  const [mode, setMode] = useState("general");
  const [format, setFormat] = useState("text");
  const [uploadDomain, setUploadDomain] = useState("");

  const [files, setFiles] = useState([]);
  const [restrictFile, setRestrictFile] = useState(false);
  const [selectedFile, setSelectedFile] = useState("");

  const messagesEndRef = useRef(null);
  const uploadInputRef = useRef(null);

  const isAdmin = user?.roles?.includes("admin");

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  };

  const loadMessages = async () => {
    if (!activeChat) return;
    const data = await fetchMessages(activeChat);
    setMessages(data);
  };

  const loadFiles = async () => {
    const data = await fetchMyFiles();
    setFiles(data);

    // 🔥 auto-clear deleted selection
    if (
      selectedFile &&
      !data.some((f) => f.file_id === selectedFile)
    ) {
      setSelectedFile("");
      setRestrictFile(false);
    }
  };

  useEffect(() => {
    if (activeChat) {
      loadMessages();
    }
  }, [activeChat]);

  useEffect(() => {
    loadFiles();
  }, [fileRefreshKey]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (error) {
      alert(error);
      setError("");
    }
  }, [error]);

  const handleSend = async () => {
    if (!input.trim() || !activeChat) return;
    setError("");

    if (restrictFile && !selectedFile) {
      alert("Please select a file");
      return;
    }

    setLoading(true);

    const payload = {
      message: input,
      mode,
      format,
    };

    if (restrictFile && selectedFile) {
      payload.file_id = selectedFile;
    }

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const response = await sendMessage(activeChat, payload);

      const assistantMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: response.answer,
        format,
        sources: response.sources || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const backendError =
        err?.response?.data?.detail || "Error sending message";
      setError(backendError);
    }

    setLoading(false);
  };

  const handlePickFile = () => {
    setUploadStatus("");
    uploadInputRef.current?.click();
  };

  const handleUploadFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file) return;

    if (isAdmin && !uploadDomain) {
      setUploadStatus("Admin must select a domain before upload.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    if (isAdmin) {
      formData.append("file_domain", uploadDomain);
    }

    try {
      setUploading(true);
      setUploadStatus("");

      await API.post("/upload/file", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setUploadStatus(`Uploaded: ${file.name}`);
      await loadFiles();
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (err) {
      setUploadStatus(err?.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  if (!activeChat)
    return <p>Select or create a chat to start.</p>;

  return (
    <>
      <div style={styles.messages}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              ...styles.message,
              alignSelf:
                msg.role === "user" ? "flex-end" : "flex-start",
              background:
                msg.role === "user" ? "#d1e7ff" : "#f1f1f1",
            }}
          >
            <div>
              {msg.role === "assistant" && msg.format === "markdown" ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                msg.content
              )}
            </div>

            {msg.role === "assistant" &&
              msg.sources &&
              msg.sources.length > 0 && (
                <details style={{ marginTop: "8px" }}>
                  <summary>📚 Sources</summary>
                  {msg.sources.map((src, index) => (
                    <div key={index} style={styles.sourceBox}>
                      <strong>File ID:</strong> {src.file_id}
                      <br />
                      <strong>Chunk:</strong> {src.chunk_id}
                      <br />
                      <p>{src.text}</p>
                    </div>
                  ))}
                </details>
              )}
          </div>
        ))}

        {loading && <div>Thinking...</div>}
        <div ref={messagesEndRef} />
      </div>

      <div style={styles.controlsArea}>
        <select value={mode} onChange={(e) => setMode(e.target.value)} style={styles.modeSelect}>
          <option value="general">General</option>
          <option value="legal">Legal</option>
          <option value="finance">Finance</option>
          <option value="academic">Academic</option>
          <option value="healthcare">Healthcare</option>
          <option value="business">Business</option>
        </select>

        <select value={format} onChange={(e) => setFormat(e.target.value)} style={styles.formatSelect}>
          <option value="text">Text</option>
          <option value="markdown">Markdown</option>
          <option value="json">JSON</option>
          <option value="table">Table</option>
        </select>

        <label style={styles.restrictLabel}>
          <input
            type="checkbox"
            checked={restrictFile}
            onChange={(e) => setRestrictFile(e.target.checked)}
          />
          Restrict to file
        </label>

        {restrictFile && (
          <select
            value={selectedFile}
            onChange={(e) => setSelectedFile(e.target.value)}
            style={styles.fileSelect}
          >
            <option value="">Select file</option>
            {files.map((file) => (
              <option key={file.file_id} value={file.file_id}>
                {file.filename}
              </option>
            ))}
          </select>
        )}
      </div>

      <div style={styles.inputArea}>
        {isAdmin && (
          <select
            value={uploadDomain}
            onChange={(e) => setUploadDomain(e.target.value)}
            style={styles.uploadDomainSelect}
          >
            <option value="">Select domain</option>
            <option value="legal">Legal</option>
            <option value="healthcare">Healthcare</option>
            <option value="finance">Finance</option>
            <option value="academic">Academic</option>
            <option value="business">Business</option>
          </select>
        )}

        <input
          ref={uploadInputRef}
          type="file"
          onChange={handleUploadFile}
          style={{ display: "none" }}
        />

        <button
          type="button"
          onClick={handlePickFile}
          disabled={uploading || (isAdmin && !uploadDomain)}
          style={styles.plusBtn}
          title={
            isAdmin && !uploadDomain
              ? "Select a domain first"
              : "Upload document"
          }
        >
          {uploading ? "..." : "+"}
        </button>

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          style={styles.input}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSend();
          }}
        />
        <button onClick={handleSend} disabled={loading}>
          Send
        </button>
      </div>

      {uploadStatus && <p style={styles.uploadStatus}>{uploadStatus}</p>}
    </>
  );
}

const styles = {
  messages: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    overflowY: "auto",
  },
  message: {
    padding: "10px",
    borderRadius: "8px",
    maxWidth: "70%",
    whiteSpace: "pre-wrap",
  },
  controlsArea: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
    marginTop: "10px",
    padding: "8px 0",
    borderTop: "1px solid #eee",
    flexWrap: "wrap",
  },
  modeSelect: {
    padding: "6px 8px",
    borderRadius: "6px",
    border: "1px solid #d0d5dd",
    background: "#fff",
    fontSize: "13px",
  },
  formatSelect: {
    padding: "6px 8px",
    borderRadius: "6px",
    border: "1px solid #d0d5dd",
    background: "#fff",
    fontSize: "13px",
  },
  restrictLabel: {
    fontSize: "13px",
    display: "flex",
    alignItems: "center",
    gap: "4px",
    cursor: "pointer",
  },
  fileSelect: {
    padding: "6px 8px",
    borderRadius: "6px",
    border: "1px solid #d0d5dd",
    background: "#fff",
    fontSize: "13px",
  },
  inputArea: {
    display: "flex",
    gap: "10px",
    marginTop: "10px",
    alignItems: "center",
  },
  input: {
    flex: 1,
    padding: "8px",
  },
  uploadDomainSelect: {
    padding: "7px 8px",
    borderRadius: "8px",
    border: "1px solid #d0d5dd",
    background: "#fff",
  },
  plusBtn: {
    width: "34px",
    height: "34px",
    borderRadius: "50%",
    border: "1px solid #d0d5dd",
    background: "#f8fafc",
    color: "#1d2939",
    fontSize: "20px",
    lineHeight: 1,
    cursor: "pointer",
  },
  sourceBox: {
    background: "#fff",
    padding: "8px",
    borderRadius: "6px",
    marginTop: "5px",
  },
  error: {
    color: "#b42318",
    background: "#fef3f2",
    border: "1px solid #fecdca",
    borderRadius: "8px",
    padding: "10px",
  },
  uploadStatus: {
    marginTop: "8px",
    fontSize: "13px",
    color: "#475467",
  },
};