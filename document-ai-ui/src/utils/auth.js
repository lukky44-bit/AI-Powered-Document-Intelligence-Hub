import { jwtDecode } from "jwt-decode";

export function getUserRoles() {
  const token = localStorage.getItem("token");
  if (!token) return [];

  try {
    const decoded = jwtDecode(token);
    return decoded.roles || [];
  } catch {
    return [];
  }
}

export function isTokenExpired(token) {
  if (!token) return true;

  try {
    const decoded = jwtDecode(token);
    if (!decoded?.exp) return true;

    const nowInSeconds = Math.floor(Date.now() / 1000);
    return decoded.exp <= nowInSeconds;
  } catch {
    return true;
  }
}
