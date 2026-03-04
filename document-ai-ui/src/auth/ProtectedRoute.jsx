import { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "./AuthContext";

export default function ProtectedRoute({ children }) {
  const { token, user } = useContext(AuthContext);

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
