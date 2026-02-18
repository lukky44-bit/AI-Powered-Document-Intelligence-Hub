import jwt_decode from "jwt-decode";

export function getUserRoles() {
  const token = localStorage.getItem("token");
  if (!token) return [];

  try {
    const decoded = jwt_decode(token);
    return decoded.roles || [];
  } catch {
    return [];
  }
}
