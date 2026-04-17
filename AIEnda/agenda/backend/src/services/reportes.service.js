// src/services/reportes.service.js
// Genera reportes dinámicamente (sin persistir en BD).

const pool     = require('../db/pool');
const REPORTES = require('../db/queries/reportes.queries');

async function ocupacionPorMedico(fechaInicio, fechaFin) {
  const [rows] = await pool.execute(REPORTES.OCUPACION_POR_MEDICO, [fechaInicio, fechaFin]);
  return rows;
}

async function ocupacionPorSede(fechaInicio, fechaFin) {
  const [rows] = await pool.execute(REPORTES.OCUPACION_POR_SEDE, [fechaInicio, fechaFin]);
  return rows;
}

async function inasistencias(fechaInicio, fechaFin) {
  const [rows] = await pool.execute(REPORTES.INASISTENCIAS_POR_RANGO, [fechaInicio, fechaFin]);
  return rows;
}

async function cancelaciones(fechaInicio, fechaFin) {
  const [rows] = await pool.execute(REPORTES.CANCELACIONES_POR_RANGO, [fechaInicio, fechaFin]);
  return rows;
}

async function citasPorCanal(fechaInicio, fechaFin) {
  const [rows] = await pool.execute(REPORTES.CITAS_POR_CANAL, [fechaInicio, fechaFin]);
  return rows;
}

module.exports = { ocupacionPorMedico, ocupacionPorSede, inasistencias, cancelaciones, citasPorCanal };
