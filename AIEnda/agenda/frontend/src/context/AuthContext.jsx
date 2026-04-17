// src/context/AuthContext.jsx
// Contexto global de autenticación. Provee usuario, rol y funciones de login/logout.

import { createContext, useContext, useState, useCallback } from 'react';
import { loginApi } from '../api/auth.api';

const AuthContext = createContext(null);

function parseJwt(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const tokenGuardado = localStorage.getItem('token');
  const [token,   setToken]   = useState(tokenGuardado);
  const [usuario, setUsuario] = useState(tokenGuardado ? parseJwt(tokenGuardado) : null);

  const login = useCallback(async (usuarioId, contrasena, canal = 'plataforma_web') => {
    const { data } = await loginApi({ usuarioId, contrasena, canal });
    localStorage.setItem('token', data.token);
    setToken(data.token);
    setUsuario(parseJwt(data.token));
    return { primerLogin: data.primerLogin };
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
    setUsuario(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, usuario, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
