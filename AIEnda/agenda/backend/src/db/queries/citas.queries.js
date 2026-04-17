// src/db/queries/citas.queries.js
// Consultas SQL relacionadas con la tabla `citas`.

const CITAS = {
  BUSCAR_POR_ID: `
    SELECT c.id, c.fecha, c.hora_inicio, c.hora_fin, c.estado, c.canal,
           c.paciente_id, c.medico_id, c.sede_id, c.created_at,
           u.nombre AS paciente, m.nombre AS medico,
           e.nombre AS especialidad, s.nombre AS sede
    FROM citas c
    INNER JOIN usuarios u ON c.paciente_id = u.id
    INNER JOIN medicos m ON c.medico_id = m.id
    INNER JOIN especialidades e ON m.especialidad_id = e.id
    INNER JOIN sedes s ON c.sede_id = s.id
    WHERE c.id = ?
    LIMIT 1
  `,

  LISTAR_POR_PACIENTE: `
    SELECT c.id, c.fecha, c.hora_inicio, c.hora_fin, c.estado, c.canal,
           m.nombre AS medico, e.nombre AS especialidad, s.nombre AS sede
    FROM citas c
    INNER JOIN medicos m ON c.medico_id = m.id
    INNER JOIN especialidades e ON m.especialidad_id = e.id
    INNER JOIN sedes s ON c.sede_id = s.id
    WHERE c.paciente_id = ?
    ORDER BY c.fecha DESC, c.hora_inicio DESC
  `,

  LISTAR_POR_MEDICO_Y_FECHA: `
    SELECT c.id, c.fecha, c.hora_inicio, c.hora_fin, c.estado, c.canal,
           u.nombre AS paciente, u.telefono AS telefono_paciente
    FROM citas c
    INNER JOIN usuarios u ON c.paciente_id = u.id
    WHERE c.medico_id = ? AND c.fecha = ?
    ORDER BY c.hora_inicio ASC
  `,

  LISTAR_POR_MEDICO_RANGO: `
    SELECT c.id, c.fecha, c.hora_inicio, c.hora_fin, c.estado,
           u.nombre AS paciente
    FROM citas c
    INNER JOIN usuarios u ON c.paciente_id = u.id
    WHERE c.medico_id = ? AND c.fecha BETWEEN ? AND ?
    ORDER BY c.fecha ASC, c.hora_inicio ASC
  `,

  // SELECT ... FOR UPDATE para evitar race condition al reservar
  VERIFICAR_DISPONIBILIDAD_LOCK: `
    SELECT id FROM citas
    WHERE medico_id = ? AND fecha = ? AND hora_inicio = ?
      AND estado NOT IN ('cancelada')
    FOR UPDATE
  `,

  CREAR: `
    INSERT INTO citas (fecha, hora_inicio, hora_fin, estado, canal,
                       paciente_id, medico_id, sede_id)
    VALUES (?, ?, ?, 'agendada', ?, ?, ?, ?)
  `,

  ACTUALIZAR_ESTADO: `
    UPDATE citas
    SET estado = ?, updated_at = NOW()
    WHERE id = ?
  `,

  CANCELAR: `
    UPDATE citas
    SET estado = 'cancelada', updated_at = NOW()
    WHERE id = ?
  `,

  REASIGNAR: `
    UPDATE citas
    SET medico_id = ?, fecha = ?, hora_inicio = ?, hora_fin = ?,
        updated_at = NOW()
    WHERE id = ?
  `,

  LISTAR_POR_SEDE_Y_FECHA: `
    SELECT c.id, c.fecha, c.hora_inicio, c.hora_fin, c.estado, c.canal,
           u.nombre AS paciente, m.nombre AS medico, e.nombre AS especialidad
    FROM citas c
    INNER JOIN usuarios u ON c.paciente_id = u.id
    INNER JOIN medicos m ON c.medico_id = m.id
    INNER JOIN especialidades e ON m.especialidad_id = e.id
    WHERE c.sede_id = ? AND c.fecha = ?
    ORDER BY c.hora_inicio ASC
  `,
};

module.exports = CITAS;
