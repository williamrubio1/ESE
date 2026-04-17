// src/utils/avatar.js
// Genera datos de avatar (iniciales + color) para médicos.
// No se almacena imagen; el frontend renderiza el avatar con estos datos.

const COLORES = [
  '#007BFF', '#28A745', '#DC3545', '#FFC107', '#6F42C1',
  '#17A2B8', '#E83E8C', '#FD7E14', '#20C997', '#6C757D',
];

/**
 * @param {string} nombre - Nombre completo del médico
 * @returns {{ iniciales: string, color: string }}
 */
function generarAvatar(nombre) {
  const palabras = nombre.trim().split(/\s+/);
  const iniciales = palabras.length >= 2
    ? `${palabras[0][0]}${palabras[1][0]}`.toUpperCase()
    : palabras[0].substring(0, 2).toUpperCase();

  // Color determinístico basado en el nombre
  let hash = 0;
  for (const ch of nombre) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  const color = COLORES[hash % COLORES.length];

  return { iniciales, color };
}

module.exports = { generarAvatar };
