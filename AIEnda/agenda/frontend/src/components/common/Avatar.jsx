// src/components/common/Avatar.jsx
// Renderiza un avatar con iniciales y color determinístico.

const COLORES = [
  '#007BFF','#28A745','#DC3545','#FFC107','#6F42C1',
  '#17A2B8','#E83E8C','#FD7E14','#20C997','#6C757D',
];

function generarAvatar(nombre = '') {
  const palabras = nombre.trim().split(/\s+/);
  const iniciales = palabras.length >= 2
    ? `${palabras[0][0]}${palabras[1][0]}`.toUpperCase()
    : nombre.substring(0, 2).toUpperCase();
  let hash = 0;
  for (const ch of nombre) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return { iniciales, color: COLORES[hash % COLORES.length] };
}

export default function Avatar({ nombre, size = 40 }) {
  const { iniciales, color } = generarAvatar(nombre);
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      backgroundColor: color, color: '#fff',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontWeight: 'bold', fontSize: size * 0.38, userSelect: 'none',
    }}>
      {iniciales}
    </div>
  );
}
