import { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "./AuthContext";
import { isTokenExpired } from "../utils/auth";

export default function ProtectedRoute({ children }) {
  const { token } = useContext(AuthContext);

  if (!token || isTokenExpired(token)) {
    return <Navigate to="/login" />;
  }

  return children;
}
