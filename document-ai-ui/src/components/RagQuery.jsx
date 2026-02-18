import { useState } from "react";

export default function RagQuery({ selectedFile }) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("general");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!query.trim()) return;

    const token = localStorage.getItem("token");

    const bodyData = {
      query: query,
      mode: mode,
    };

    // Include file_id only if user selected a file
    if (selectedFile) {
      bodyData.file_id = selectedFile;
    }

    try {
      setLoading(true);
      setAnswer("");

      const response = await fetch("http://localhost:8000/rag/answer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(bodyData),
      });

      const data = await response.json();

      if (response.ok) {
        setAnswer(data.answer);
      } else {
        setAnswer("Error: " + data.detail);
      }
    } catch (error) {
      setAnswer("Server error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h3>💬 Ask a Question</h3>

      {/* Mode Selector */}
      <div style={{ marginBottom: "10px" }}>
        <label style={{ marginRight: "10px" }}>Mode:</label>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          style={{ padding: "6px" }}
        >
          <option value="general">General</option>
          <option value="legal">Legal</option>
          <option value="healthcare">Healthcare</option>
          <option value="finance">Finance</option>
          <option value="academic">Academic</option>
          <option value="business">Business</option>
        </select>
      </div>

      {/* Query Input */}
      <input
        type="text"
        placeholder="Ask something..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ width: "60%", padding: "6px" }}
      />

      <button onClick={handleAsk} style={{ marginLeft: "10px" }}>
        {loading ? "Thinking..." : "Ask"}
      </button>

      {/* Answer Section */}
      {answer && (
        <div style={{ marginTop: "20px" }}>
          <strong>Answer:</strong>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}
