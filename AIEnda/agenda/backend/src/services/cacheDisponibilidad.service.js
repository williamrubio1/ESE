// src/services/cacheDisponibilidad.service.js
// Caché Redis para disponibilidad de médicos. TTL = 90 segundos.

const redis         = require('../config/redis');
const pool          = require('../db/pool');
const DISPONIBILIDAD = require('../db/queries/disponibilidad.queries');

const TTL = 90; // segundos

function clave(medicoId, fecha) {
  return `disponibilidad:${medicoId}:${fecha}`;
}

/**
 * Retorna los turnos libres de un médico en una fecha.
 * Primero busca en Redis; si no existe, consulta MySQL y almacena.
 */
async function obtener(medicoId, fecha) {
  const k       = clave(medicoId, fecha);
  const cached  = await redis.get(k);

  if (cached) {
    return JSON.parse(cached);
  }

  const [rows] = await pool.execute(
    DISPONIBILIDAD.TURNOS_LIBRES_POR_MEDICO_Y_FECHA,
    [medicoId, fecha],
  );

  await redis.set(k, JSON.stringify(rows), 'EX', TTL);
  return rows;
}

/** Invalida el caché de un médico/fecha al modificar disponibilidad o citas. */
async function invalidar(medicoId, fecha) {
  await redis.del(clave(medicoId, fecha));
}

module.exports = { obtener, invalidar };
