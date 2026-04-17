// src/utils/auditoria.js
// Función utilitaria para registrar acciones en la tabla `auditoria`.
// Se usa desde cualquier servicio o controlador.

const pool = require('../db/pool');
const AUDITORIA = require('../db/queries/auditoria.queries');

/**
 * @param {object} params
 * @param {number|string} params.usuarioId
 * @param {string} params.accion    - login | cambio_contrasena | agendar_cita | cancelar_cita | reasignar_cita
 * @param {string} params.entidad   - usuarios | citas | medicos | etc.
 * @param {number|null} params.entidadId
 * @param {string} params.detalle   - descripción libre
 * @param {string} params.canal     - plataforma_web | whatsapp | n8n | recepcion | administrador
 * @param {string} params.ip
 */
async function registrarAuditoria({ usuarioId, accion, entidad, entidadId = null, detalle = '', canal, ip }) {
  try {
    await pool.execute(AUDITORIA.REGISTRAR, [
      usuarioId, accion, entidad, entidadId, detalle, canal, ip,
    ]);
  } catch (err) {
    // La auditoría no debe interrumpir el flujo principal
    console.error('[Auditoría] Error al registrar:', err.message);
  }
}

module.exports = { registrarAuditoria };
