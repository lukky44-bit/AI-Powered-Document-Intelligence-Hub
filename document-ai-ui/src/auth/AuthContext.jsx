import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { jwtDecode } from "jwt-decode";
import { setAuthToken } from "../api/client";

export const AuthContext = createContext();

const TOKEN_KEY = "token";

function parseToken(jwt) {
  if (!jwt) return null;

  try {
    const decoded = jwtDecode(jwt);
    const nowInSeconds = Math.floor(Date.now() / 1000);
    const exp = Number(decoded?.exp || 0);

    if (!exp || exp <= nowInSeconds) {
      return null;
    }

    const roles = Array.isArray(decoded?.roles)
      ? decoded.roles
      : decoded?.roles
      ? [decoded.roles]
      : [];

    const email = decoded?.email || decoded?.sub || "";

    return {
      token: jwt,
      user: { email, roles },
      exp,
    };
  } catch {
    return null;
  }
}

function getInitialSession() {
  const storedToken = localStorage.getItem(TOKEN_KEY);
  const parsed = parseToken(storedToken);

  if (!parsed) {
    localStorage.removeItem(TOKEN_KEY);
    return { token: null, user: null, exp: null };
  }

  return { token: parsed.token, user: parsed.user, exp: parsed.exp };
}

export const AuthProvider = ({ children }) => {
  const initialSession = getInitialSession();
  const [token, setToken] = useState(initialSession.token);
  const [user, setUser] = useState(initialSession.user);
  const [exp, setExp] = useState(initialSession.exp);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setAuthToken(null);
    setToken(null);
    setUser(null);
    setExp(null);
  }, []);

  const login = useCallback(
    (jwt) => {
      const parsed = parseToken(jwt);

      if (!parsed) {
        logout();
        return false;
      }

      localStorage.setItem(TOKEN_KEY, parsed.token);
      setToken(parsed.token);
      setUser(parsed.user);
      setExp(parsed.exp);
      return true;
    },
    [logout]
  );

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  useEffect(() => {
    if (!exp) return undefined;

    const msUntilExpiry = exp * 1000 - Date.now();
    if (msUntilExpiry <= 0) {
      logout();
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      logout();
    }, msUntilExpiry);

    return () => window.clearTimeout(timeoutId);
  }, [exp, logout]);

  const value = useMemo(
    () => ({ token, user, login, logout }),
    [token, user, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};