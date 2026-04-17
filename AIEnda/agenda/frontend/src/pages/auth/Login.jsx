// src/pages/auth/Login.jsx

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const ROL_RUTA = {
  paciente:      '/paciente',
  medico:        '/medico',
  administrador: '/admin',
  recepcion:     '/recepcion',
};

export default function Login() {
  const { login }   = useAuth();
  const navigate    = useNavigate();
  const [form, setForm]   = useState({ usuarioId: '', contrasena: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { primerLogin } = await login(form.usuarioId, form.contrasena);
      if (primerLogin) {
        navigate('/cambiar-contrasena');
      } else {
        // Decodificar rol del token para redirigir
        const token   = localStorage.getItem('token');
        const payload = JSON.parse(atob(token.split('.')[1]));
        navigate(ROL_RUTA[payload.rol] || '/');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Agenda — Iniciar sesión</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label>ID de usuario</label>
          <input name="usuarioId" value={form.usuarioId} onChange={handleChange} required />
        </div>
        <div>
          <label>Contraseña</label>
          <input type="password" name="contrasena" value={form.contrasena} onChange={handleChange} required />
        </div>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Ingresando...' : 'Ingresar'}
        </button>
      </form>
    </div>
  );
}
