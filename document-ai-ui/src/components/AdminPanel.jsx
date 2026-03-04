import { useContext, useState } from "react";
import API from "../api/client";
import { AuthContext } from "../auth/AuthContext";

export default function AdminPanel() {
  const { user } = useContext(AuthContext);

  const [isOpen, setIsOpen] = useState(true);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState(["lawyer"]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const isAdmin = user?.roles?.includes("admin");

  if (!isAdmin) {
    return null;
  }

  const handleRoleChange = async () => {
    if (!email.trim()) {
      setMessage("Please enter user email.");
      return;
    }

    try {
      setLoading(true);
      setMessage("");

      await API.put("/admin/users/roles", {
        email,
        roles: role,
      });

      setMessage("Role updated successfully!");
      setEmail("");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to update role.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={{ margin: 0 }}>🛠 Admin Role Management</h3>
        <button
          onClick={() => setIsOpen((prev) => !prev)}
          style={styles.toggleButton}
          aria-expanded={isOpen}
        >
          {isOpen ? "Collapse" : "Expand"}
        </button>
      </div>

      {isOpen && (
        <>
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
                  Array.from(
                    e.target.selectedOptions,
                    (option) => option.value
                  )
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
        </>
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
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
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
  toggleButton: {
    padding: "6px 10px",
    border: "1px solid #d0d7de",
    borderRadius: "6px",
    background: "#f6f8fa",
    color: "#24292f",
    cursor: "pointer",
  },
};
