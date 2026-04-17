// src/db/queries/reportes.queries.js
// Consultas SQL para generación dinámica de reportes.
// Los reportes NO se persisten; se generan on-demand.

const REPORTES = {
  OCUPACION_POR_MEDICO: `
    SELECT m.nombre AS medico, e.nombre AS especialidad,
           COUNT(c.id) AS total_citas,
           SUM(c.estado = 'atendida') AS atendidas,
           SUM(c.estado = 'cancelada') AS canceladas,
           SUM(c.estado = 'inasistencia') AS inasistencias
    FROM citas c
    INNER JOIN medicos m ON c.medico_id = m.id
    INNER JOIN especialidades e ON m.especialidad_id = e.id
    WHERE c.fecha BETWEEN ? AND ?
    GROUP BY m.id, m.nombre, e.nombre
    ORDER BY total_citas DESC
  `,

  OCUPACION_POR_SEDE: `
    SELECT s.nombre AS sede,
           COUNT(c.id) AS total_citas,
           SUM(c.estado = 'atendida') AS atendidas,
           SUM(c.estado = 'cancelada') AS canceladas,
           SUM(c.estado = 'inasistencia') AS inasistencias
    FROM citas c
    INNER JOIN sedes s ON c.sede_id = s.id
    WHERE c.fecha BETWEEN ? AND ?
    GROUP BY s.id, s.nombre
    ORDER BY total_citas DESC
  `,

  INASISTENCIAS_POR_RANGO: `
    SELECT c.fecha, u.nombre AS paciente, m.nombre AS medico,
           e.nombre AS especialidad, s.nombre AS sede
    FROM citas c
    INNER JOIN usuarios u ON c.paciente_id = u.id
    INNER JOIN medicos m ON c.medico_id = m.id
    INNER JOIN especialidades e ON m.especialidad_id = e.id
    INNER JOIN sedes s ON c.sede_id = s.id
    WHERE c.estado = 'inasistencia'
      AND c.fecha BETWEEN ? AND ?
    ORDER BY c.fecha ASC
  `,

  CANCELACIONES_POR_RANGO: `
    SELECT c.fecha, c.canal, u.nombre AS paciente, m.nombre AS medico
    FROM citas c
    INNER JOIN usuarios u ON c.paciente_id = u.id
    INNER JOIN medicos m ON c.medico_id = m.id
    WHERE c.estado = 'cancelada'
      AND c.fecha BETWEEN ? AND ?
    ORDER BY c.fecha ASC
  `,

  CITAS_POR_CANAL: `
    SELECT c.canal, COUNT(*) AS total
    FROM citas c
    WHERE c.fecha BETWEEN ? AND ?
    GROUP BY c.canal
    ORDER BY total DESC
  `,
};

module.exports = REPORTES;
