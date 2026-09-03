import { createContext, useContext, useEffect, useState } from "react";
import api, { setToken } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null=checking, false=anon, object=auth
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("conformiste_token");
    if (!token) { setUser(false); setLoading(false); return; }
    api.get("/auth/me")
      .then(({ data }) => setUser(data))
      .catch(() => { setToken(null); setUser(false); })
      .finally(() => setLoading(false));
  }, []);

  const handleAuth = (data) => {
    setToken(data.access_token);
    setUser(data.user);
  };

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    handleAuth(data);
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    handleAuth(data);
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch (e) { /* noop */ }
    setToken(null);
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
