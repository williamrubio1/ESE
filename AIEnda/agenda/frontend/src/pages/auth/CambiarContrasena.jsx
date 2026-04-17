// src/pages/auth/CambiarContrasena.jsx
// Primera vez: fuerza al usuario a cambiar la contraseña inicial.

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAsync }   from '../../hooks/useAsync';
import { cambiarContrasenaApi } from '../../api/auth.api';

export default function CambiarContrasena() {
  const navigate = useNavigate();
  const { ejecutar, loading, error } = useAsync(cambiarContrasenaApi);
  const [form, setForm] = useState({ nuevaContrasena: '', confirmar: '' });
  const [msg,  setMsg]  = useState('');

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (form.nuevaContrasena !== form.confirmar) {
      setMsg('Las contraseñas no coinciden');
      return;
    }
    await ejecutar({ nuevaContrasena: form.nuevaContrasena });
    navigate('/');
  }

  return (
    <div>
      <h1>Cambiar contraseña</h1>
      <p>Por seguridad, debe cambiar su contraseña antes de continuar.</p>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Nueva contraseña</label>
          <input type="password" name="nuevaContrasena" value={form.nuevaContrasena} onChange={handleChange} required minLength={6} />
        </div>
        <div>
          <label>Confirmar contraseña</label>
          <input type="password" name="confirmar" value={form.confirmar} onChange={handleChange} required />
        </div>
        {(error || msg) && <p style={{ color: 'red' }}>{error || msg}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Guardando...' : 'Guardar'}
        </button>
      </form>
    </div>
  );
}
