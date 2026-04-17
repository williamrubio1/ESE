// src/utils/fechas.js
// Utilidades de fechas/horas en zona GMT-5 (Bogotá).

const ZONA = 'America/Bogota';

/** Retorna la fecha y hora actual en GMT-5 como objeto Date */
function ahoraBogota() {
  return new Date(new Date().toLocaleString('en-US', { timeZone: ZONA }));
}

/**
 * Verifica si una cita puede cancelarse (al menos 12 horas de anticipación).
 * @param {string} fecha       - 'YYYY-MM-DD'
 * @param {string} horaInicio  - 'HH:MM:SS'
 * @returns {boolean}
 */
function puedeCancelarse(fecha, horaInicio) {
  const citaDate = new Date(`${fecha}T${horaInicio}-05:00`);
  const ahora    = ahoraBogota();
  const diffHoras = (citaDate - ahora) / (1000 * 60 * 60);
  return diffHoras >= 12;
}

/**
 * Calcula la hora de fin dado un inicio y duración en minutos.
 * @param {string} horaInicio - 'HH:MM'
 * @param {number} duracionMin
 * @returns {string} 'HH:MM:SS'
 */
function calcularHoraFin(horaInicio, duracionMin = 20) {
  const [h, m] = horaInicio.split(':').map(Number);
  const totalMin = h * 60 + m + duracionMin;
  const hf = String(Math.floor(totalMin / 60)).padStart(2, '0');
  const mf = String(totalMin % 60).padStart(2, '0');
  return `${hf}:${mf}:00`;
}

module.exports = { ahoraBogota, puedeCancelarse, calcularHoraFin };
