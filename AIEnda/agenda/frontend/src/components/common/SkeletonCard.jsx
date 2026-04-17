// src/components/common/SkeletonCard.jsx
// Tarjeta skeleton genérica para estados de carga.

export default function SkeletonCard({ filas = 3 }) {
  const estiloLinea = (ancho) => ({
    height: 14, borderRadius: 4, backgroundColor: '#e0e0e0',
    marginBottom: 10, width: ancho,
    animation: 'pulse 1.4s ease-in-out infinite',
  });
  return (
    <div style={{ padding: '1rem', borderRadius: 8, background: '#f9f9f9', marginBottom: 12 }}>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }`}</style>
      {Array.from({ length: filas }).map((_, i) => (
        <div key={i} style={estiloLinea(i === 0 ? '60%' : '90%')} />
      ))}
    </div>
  );
}
