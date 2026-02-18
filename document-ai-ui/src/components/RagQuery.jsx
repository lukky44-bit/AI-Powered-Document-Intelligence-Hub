import { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function RagQuery({ selectedFile }) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("general");
  const [responseFormat, setResponseFormat] = useState("text");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const token = localStorage.getItem("token");

  const handleAsk = async () => {
    if (!query.trim()) return;

    const bodyData = {
      query,
      mode,
      format: responseFormat,
    };

    if (selectedFile) {
      bodyData.file_id = selectedFile;
    }

    try {
      setLoading(true);
      setAnswer("");

      const response = await fetch(
        "http://localhost:8000/rag/answer",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(bodyData),
        }
      );

      const data = await response.json();

      if (response.ok) {
        setAnswer(data.answer);
      } else {
        setAnswer("Error: " + data.detail);
      }
    } catch {
      setAnswer("Server error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h3>💬 Ask a Question</h3>

      {/* Mode */}
      <div style={{ marginBottom: "8px" }}>
        <label>Mode: </label>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          <option value="general">General</option>
          <option value="legal">Legal</option>
          <option value="healthcare">Healthcare</option>
          <option value="finance">Finance</option>
          <option value="academic">Academic</option>
          <option value="business">Business</option>
        </select>
      </div>

      {/* Response Format */}
      <div style={{ marginBottom: "8px" }}>
        <label>Response Format: </label>
        <select
          value={responseFormat}
          onChange={(e) => setResponseFormat(e.target.value)}
        >
          <option value="text">Text</option>
          <option value="markdown">Markdown</option>
          <option value="json">JSON</option>
          <option value="table">Table</option>
        </select>
      </div>

      {/* Query */}
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask something..."
        style={{ width: "60%", padding: "6px" }}
      />

      <button
        onClick={handleAsk}
        style={{ marginLeft: "10px" }}
      >
        {loading ? "Thinking..." : "Ask"}
      </button>

      {/* Render Answer */}
      {answer && (
        <div style={{ marginTop: "20px" }}>
          <strong>Answer:</strong>

          {responseFormat === "markdown" ||
          responseFormat === "table" ? (
            <ReactMarkdown>{answer}</ReactMarkdown>
          ) : responseFormat === "json" ? (
            <pre>{JSON.stringify(JSON.parse(answer), null, 2)}</pre>
          ) : (
            <p>{answer}</p>
          )}
        </div>
      )}
    </div>
  );
}
