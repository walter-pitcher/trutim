import { createContext, useContext, useState, useEffect } from 'react';
import { auth, users } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access');
    if (token) {
      users.me()
        .then(({ data }) => setUser(data))
        .catch(() => {
          localStorage.removeItem('access');
          localStorage.removeItem('refresh');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (username, password) => {
    const { data } = await auth.login(username, password);
    localStorage.setItem('access', data.access);
    localStorage.setItem('refresh', data.refresh);
    setUser(data.user);
    return data;
  };

  const register = async (formData) => {
    await auth.register(formData);
    return login(formData.username, formData.password);
  };

  const logout = () => {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    setUser(null);
  };

  const refreshUser = async () => {
    const { data } = await users.me();
    setUser(data);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
