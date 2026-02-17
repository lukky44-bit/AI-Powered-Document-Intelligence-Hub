import { useState, useContext } from "react";
import { useNavigate, Link } from "react-router-dom";
import API from "../api/client";
import { AuthContext } from "../auth/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const response = await API.post("/auth/login", {
        email,
        password,
      });

      const token = response.data.token;
      login(token);
      navigate("/");
    } catch (err) {
      setError(
        err.response?.data?.detail || "Login failed"
      );
    }
  };

  return (
    <div style={styles.container}>
      <h2>🔐 Login</h2>

      <form onSubmit={handleLogin} style={styles.form}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button type="submit">Login</button>
      </form>

      {error && <p style={styles.error}>{error}</p>}

      <p>
        New user? <Link to="/signup">Sign up</Link>
      </p>
    </div>
  );
}

const styles = {
  container: {
    maxWidth: "400px",
    margin: "80px auto",
    padding: "20px",
    border: "1px solid #ddd",
    borderRadius: "6px",
    textAlign: "center",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  error: {
    color: "red",
    marginTop: "10px",
  },
};
