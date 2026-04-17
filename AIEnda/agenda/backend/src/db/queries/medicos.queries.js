// src/db/queries/medicos.queries.js
// Consultas SQL relacionadas con la tabla `medicos`.

const MEDICOS = {
  LISTAR_ACTIVOS: `
    SELECT m.id, m.nombre, e.nombre AS especialidad, m.estado, m.ruta_foto,
           s.nombre AS sede
    FROM medicos m
    INNER JOIN especialidades e ON m.especialidad_id = e.id
    LEFT JOIN sedes s ON m.sede_id = s.id
    WHERE m.estado = 'activo'
    ORDER BY m.nombre ASC
  `,

  BUSCAR_POR_ID: `
    SELECT m.id, m.nombre, e.nombre AS especialidad, m.disponibilidad,
           m.estado, m.ruta_foto, m.created_at
    FROM medicos m
    INNER JOIN especialidades e ON m.especialidad_id = e.id
    WHERE m.id = ?
    LIMIT 1
  `,

  LISTAR_POR_ESPECIALIDAD: `
    SELECT m.id, m.nombre, m.ruta_foto, m.estado
    FROM medicos m
    WHERE m.especialidad_id = ? AND m.estado = 'activo'
    ORDER BY m.nombre ASC
  `,

  LISTAR_POR_SEDE: `
    SELECT m.id, m.nombre, e.nombre AS especialidad, m.ruta_foto
    FROM medicos m
    INNER JOIN especialidades e ON m.especialidad_id = e.id
    WHERE m.sede_id = ? AND m.estado = 'activo'
    ORDER BY m.nombre ASC
  `,

  CREAR: `
    INSERT INTO medicos (nombre, especialidad_id, sede_id, disponibilidad, estado)
    VALUES (?, ?, ?, ?, 'activo')
  `,

  ACTUALIZAR: `
    UPDATE medicos
    SET nombre = ?, especialidad_id = ?, sede_id = ?, disponibilidad = ?,
        updated_at = NOW()
    WHERE id = ?
  `,

  CAMBIAR_ESTADO: `
    UPDATE medicos
    SET estado = ?, updated_at = NOW()
    WHERE id = ?
  `,

  // Detectar médicos con disponibilidad activa sin citas en las próximas N horas
  ESPACIOS_VACIOS_PROXIMAS_HORAS: `
    SELECT m.id AS medico_id, m.nombre AS medico, e.nombre AS especialidad,
           s.nombre AS sede, t.fecha, t.hora_inicio, t.hora_fin
    FROM turnos_disponibles t
    INNER JOIN medicos m ON t.medico_id = m.id
    INNER JOIN especialidades e ON m.especialidad_id = e.id
    INNER JOIN sedes s ON m.sede_id = s.id
    WHERE m.estado = 'activo'
      AND t.fecha = CURDATE()
      AND TIMESTAMPDIFF(MINUTE, NOW(), CONCAT(t.fecha, ' ', t.hora_inicio)) BETWEEN 0 AND ?
      AND NOT EXISTS (
        SELECT 1 FROM citas c
        WHERE c.medico_id = t.medico_id
          AND c.fecha = t.fecha
          AND c.hora_inicio = t.hora_inicio
          AND c.estado NOT IN ('cancelada')
      )
    ORDER BY t.hora_inicio ASC
  `,
};

module.exports = MEDICOS;
