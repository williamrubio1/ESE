// src/services/espaciosVacios.service.js
// Detecta turnos de médicos activos sin citas en las próximas 6 horas.

const pool    = require('../db/pool');
const MEDICOS = require('../db/queries/medicos.queries');

const VENTANA_HORAS = 6;
const VENTANA_MIN   = VENTANA_HORAS * 60;

/**
 * Retorna los turnos activos sin citas agendadas dentro de las próximas 6 horas.
 */
async function obtenerEspaciosVacios() {
  const [rows] = await pool.execute(
    MEDICOS.ESPACIOS_VACIOS_PROXIMAS_HORAS,
    [VENTANA_MIN],
  );
  return rows;
}

module.exports = { obtenerEspaciosVacios };
