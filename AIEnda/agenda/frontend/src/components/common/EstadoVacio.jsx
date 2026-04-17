// src/components/common/EstadoVacio.jsx
// Componente para pantallas sin datos.

export default function EstadoVacio({ mensaje = 'No hay datos para mostrar', accion }) {
  return (
    <div style={{ textAlign: 'center', padding: '2rem', color: '#6C757D' }}>
      <p style={{ fontSize: '1rem', marginBottom: '1rem' }}>{mensaje}</p>
      {accion && accion}
    </div>
  );
}
