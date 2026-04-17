// src/components/common/Toast.jsx
// Notificaciones flotantes reutilizables: éxito, error, advertencia.

import { useEffect } from 'react';

const COLORES = {
  exito:      { bg: '#28A745', fg: '#fff' },
  error:      { bg: '#DC3545', fg: '#fff' },
  advertencia:{ bg: '#FFC107', fg: '#343A40' },
};

export default function Toast({ mensaje, tipo = 'exito', onClose, duracion = 3500 }) {
  useEffect(() => {
    const t = setTimeout(onClose, duracion);
    return () => clearTimeout(t);
  }, [onClose, duracion]);

  const { bg, fg } = COLORES[tipo] || COLORES.exito;

  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
      backgroundColor: bg, color: fg,
      padding: '12px 20px', borderRadius: 8,
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      fontWeight: 500, cursor: 'pointer',
    }} onClick={onClose}>
      {mensaje}
    </div>
  );
}
