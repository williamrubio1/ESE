// src/services/citas.service.js
// Lógica de negocio para agendamiento, cancelación y reasignación de citas.

const pool       = require('../db/pool');
const CITAS      = require('../db/queries/citas.queries');
const { puedeCancelarse, calcularHoraFin } = require('../utils/fechas');
const { registrarAuditoria }               = require('../utils/auditoria');
const cacheDisponibilidad                  = require('./cacheDisponibilidad.service');

/**
 * Agenda una nueva cita. Usa transacción con SELECT FOR UPDATE.
 */
async function agendarCita({ fecha, horaInicio, medicoId, pacienteId, sedeId, canal, ip }) {
  const horaFin = calcularHoraFin(horaInicio, 20);
  const conn    = await pool.getConnection();

  try {
    await conn.beginTransaction();

    // Lock del turno para evitar race condition
    const [ocupado] = await conn.execute(CITAS.VERIFICAR_DISPONIBILIDAD_LOCK, [
      medicoId, fecha, horaInicio,
    ]);
    if (ocupado.length > 0) {
      await conn.rollback();
      const err = new Error('El turno ya no está disponible'); err.status = 409; throw err;
    }

    const [result] = await conn.execute(CITAS.CREAR, [
      fecha, horaInicio, horaFin, canal, pacienteId, medicoId, sedeId,
    ]);

    await conn.commit();

    // Invalidar caché de disponibilidad para este médico y fecha
    await cacheDisponibilidad.invalidar(medicoId, fecha);

    await registrarAuditoria({
      usuarioId: pacienteId,
      accion:    'agendar_cita',
      entidad:   'citas',
      entidadId: result.insertId,
      detalle:   `Cita agendada para ${fecha} ${horaInicio}`,
      canal,
      ip,
    });

    return { citaId: result.insertId };
  } catch (err) {
    await conn.rollback();
    throw err;
  } finally {
    conn.release();
  }
}

/**
 * Cancela una cita. Solo si faltan >= 12 horas.
 */
async function cancelarCita({ citaId, usuarioId, ip, canal = 'plataforma_web' }) {
  const [rows] = await pool.execute(CITAS.BUSCAR_POR_ID, [citaId]);
  const cita   = rows[0];

  if (!cita) {
    const err = new Error('Cita no encontrada'); err.status = 404; throw err;
  }
  if (!puedeCancelarse(cita.fecha, cita.hora_inicio)) {
    const err = new Error('No es posible cancelar con menos de 12 horas de anticipación');
    err.status = 422; throw err;
  }

  await pool.execute(CITAS.CANCELAR, [citaId]);
  await cacheDisponibilidad.invalidar(cita.medico_id, cita.fecha);

  await registrarAuditoria({
    usuarioId,
    accion:    'cancelar_cita',
    entidad:   'citas',
    entidadId: citaId,
    detalle:   `Cita cancelada (${cita.fecha} ${cita.hora_inicio})`,
    canal,
    ip,
  });
}

/**
 * Reasigna una cita a otro médico/fecha/hora. Uso exclusivo de Recepción y Administrador.
 */
async function reasignarCita({ citaId, nuevoMedicoId, nuevaFecha, nuevaHoraInicio, usuarioId, ip, canal }) {
  const horaFin = calcularHoraFin(nuevaHoraInicio, 20);
  const conn    = await pool.getConnection();

  try {
    await conn.beginTransaction();

    const [ocupado] = await conn.execute(CITAS.VERIFICAR_DISPONIBILIDAD_LOCK, [
      nuevoMedicoId, nuevaFecha, nuevaHoraInicio,
    ]);
    if (ocupado.length > 0) {
      await conn.rollback();
      const err = new Error('El turno destino ya no está disponible'); err.status = 409; throw err;
    }

    // Obtener cita original para invalidar caché viejo
    const [rows] = await conn.execute(CITAS.BUSCAR_POR_ID, [citaId]);
    const citaOriginal = rows[0];

    await conn.execute(CITAS.REASIGNAR, [
      nuevoMedicoId, nuevaFecha, nuevaHoraInicio, horaFin, citaId,
    ]);

    await conn.commit();

    if (citaOriginal) {
      await cacheDisponibilidad.invalidar(citaOriginal.medico_id, citaOriginal.fecha);
    }
    await cacheDisponibilidad.invalidar(nuevoMedicoId, nuevaFecha);

    await registrarAuditoria({
      usuarioId,
      accion:    'reasignar_cita',
      entidad:   'citas',
      entidadId: citaId,
      detalle:   `Reasignada a médico ${nuevoMedicoId} el ${nuevaFecha} ${nuevaHoraInicio}`,
      canal,
      ip,
    });
  } catch (err) {
    await conn.rollback();
    throw err;
  } finally {
    conn.release();
  }
}

/**
 * Retorna las citas de un paciente (historial).
 */
async function citasPorPaciente(pacienteId) {
  const [rows] = await pool.execute(CITAS.LISTAR_POR_PACIENTE, [pacienteId]);
  return rows;
}

/**
 * Retorna las citas de un médico en una fecha (vista diaria).
 */
async function citasDiariasmedico(medicoId, fecha) {
  const [rows] = await pool.execute(CITAS.LISTAR_POR_MEDICO_Y_FECHA, [medicoId, fecha]);
  return rows;
}

/**
 * Retorna citas de un médico en un rango (vista semanal/mensual).
 */
async function citasRangoMedico(medicoId, fechaInicio, fechaFin) {
  const [rows] = await pool.execute(CITAS.LISTAR_POR_MEDICO_RANGO, [medicoId, fechaInicio, fechaFin]);
  return rows;
}

module.exports = {
  agendarCita,
  cancelarCita,
  reasignarCita,
  citasPorPaciente,
  citasDiariasmedico,
  citasRangoMedico,
};
