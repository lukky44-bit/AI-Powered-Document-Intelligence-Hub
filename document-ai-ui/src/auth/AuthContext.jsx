import { createContext, useEffect, useState } from "react";
import { setAuthToken } from "../api/client";
import { isTokenExpired } from "../utils/auth";

export const AuthContext= createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => {
    const stored = localStorage.getItem("token");
    if (!stored || isTokenExpired(stored)) {
      localStorage.removeItem("token");
      return null;
    }
    return stored;
  });

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  useEffect(() => {
    if (!token) return;
    if (isTokenExpired(token)) {
      localStorage.removeItem("token");
      setToken(null);
    }
  }, [token]);

  const login = (jwt) => {
    if (isTokenExpired(jwt)) {
      localStorage.removeItem("token");
      setToken(null);
      return;
    }
    localStorage.setItem("token", jwt);
    setToken(jwt);
  };

  const logout=()=>{
    localStorage.removeItem("token");
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};