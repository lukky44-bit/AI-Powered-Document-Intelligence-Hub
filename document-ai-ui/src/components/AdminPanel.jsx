import { useState } from "react";

export default function AdminPanel() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState(["lawyer"]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRoleChange = async () => {
    if (!email.trim()) {
      setMessage("Please enter user email.");
      return;
    }

    const token = localStorage.getItem("token");

    try {
      setLoading(true);
      setMessage("");

      const response = await fetch(
        "http://localhost:8000/admin/users/roles",
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            email: email,
            roles: role,   // ✅ now always array
          }),
        }
      );

      const data = await response.json();

      if (response.ok) {
        setMessage("Role updated successfully!");
        setEmail("");
      } else {
        setMessage(data.detail || "Failed to update role.");
      }
    } catch (error) {
      setMessage("Server error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h3>🛠 Admin Role Management</h3>

      <div style={{ marginTop: "10px" }}>
        <input
          type="text"
          placeholder="User email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={styles.input}
        />

        <select
          multiple
          value={role}
          onChange={(e) =>
            setRole(
              Array.from(e.target.selectedOptions, (option) => option.value)
            )
          }
          style={styles.select}
        >
          <option value="lawyer">Lawyer</option>
          <option value="doctor">Doctor</option>
          <option value="researcher">Researcher</option>
          <option value="finance">Finance</option>
          <option value="business">Business</option>
          <option value="admin">Admin</option>
        </select>

        <button
          onClick={handleRoleChange}
          style={styles.button}
        >
          {loading ? "Updating..." : "Update Role"}
        </button>
      </div>

      {message && (
        <p style={{ marginTop: "10px", color: "#555" }}>
          {message}
        </p>
      )}
    </div>
  );
}

const styles = {
  container: {
    marginTop: "20px",
    padding: "16px",
    border: "1px solid #e5e5e5",
    borderRadius: "8px",
    background: "#fff",
  },
  input: {
    padding: "8px 10px",
    border: "1px solid #ccc",
    borderRadius: "6px",
    marginRight: "8px",
  },
  select: {
    padding: "8px 10px",
    border: "1px solid #ccc",
    borderRadius: "6px",
    marginRight: "8px",
  },
  button: {
    padding: "8px 12px",
    border: "none",
    borderRadius: "6px",
    background: "#2f6fed",
    color: "#fff",
    cursor: "pointer",
  },
};
