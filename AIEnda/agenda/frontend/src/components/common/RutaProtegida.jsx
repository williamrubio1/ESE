// src/components/common/RutaProtegida.jsx
// Redirige al login si no hay sesión. Verifica también el rol si se especifica.

import { Navigate } from 'react-router-dom';
import { useAuth }  from '../../context/AuthContext';

export default function RutaProtegida({ children, roles = [] }) {
  const { usuario } = useAuth();

  if (!usuario) return <Navigate to="/login" replace />;
  if (roles.length > 0 && !roles.includes(usuario.rol)) {
    return <Navigate to="/no-autorizado" replace />;
  }
  return children;
}
