// src/db/queries/disponibilidad.queries.js
// Consultas SQL para turnos disponibles de médicos.

const DISPONIBILIDAD = {
  TURNOS_LIBRES_POR_MEDICO_Y_FECHA: `
    SELECT t.hora_inicio, t.hora_fin
    FROM turnos_disponibles t
    WHERE t.medico_id = ? AND t.fecha = ?
      AND NOT EXISTS (
        SELECT 1 FROM citas c
        WHERE c.medico_id = t.medico_id
          AND c.fecha = t.fecha
          AND c.hora_inicio = t.hora_inicio
          AND c.estado NOT IN ('cancelada')
      )
    ORDER BY t.hora_inicio ASC
  `,

  CREAR_TURNO: `
    INSERT INTO turnos_disponibles (medico_id, fecha, hora_inicio, hora_fin)
    VALUES (?, ?, ?, ?)
  `,

  ELIMINAR_TURNO: `
    DELETE FROM turnos_disponibles
    WHERE medico_id = ? AND fecha = ? AND hora_inicio = ?
  `,

  LISTAR_TURNOS_POR_MEDICO_RANGO: `
    SELECT fecha, hora_inicio, hora_fin
    FROM turnos_disponibles
    WHERE medico_id = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC, hora_inicio ASC
  `,
};

module.exports = DISPONIBILIDAD;
