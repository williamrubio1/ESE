// src/db/queries/auditoria.queries.js
// Consultas SQL para la tabla `auditoria`.

const AUDITORIA = {
  REGISTRAR: `
    INSERT INTO auditoria (usuario_id, accion, entidad, entidad_id, detalle, canal, ip, timestamp_accion)
    VALUES (?, ?, ?, ?, ?, ?, ?, NOW())
  `,

  LISTAR_POR_USUARIO: `
    SELECT id, accion, entidad, entidad_id, detalle, canal, ip, timestamp_accion
    FROM auditoria
    WHERE usuario_id = ?
    ORDER BY timestamp_accion DESC
    LIMIT ? OFFSET ?
  `,

  LISTAR_POR_ACCION_Y_RANGO: `
    SELECT a.id, u.nombre AS usuario, a.accion, a.entidad, a.detalle,
           a.canal, a.ip, a.timestamp_accion
    FROM auditoria a
    INNER JOIN usuarios u ON a.usuario_id = u.id
    WHERE a.accion = ?
      AND a.timestamp_accion BETWEEN ? AND ?
    ORDER BY a.timestamp_accion DESC
  `,

  LISTAR_RECIENTE: `
    SELECT a.id, u.nombre AS usuario, a.accion, a.entidad, a.canal,
           a.ip, a.timestamp_accion
    FROM auditoria a
    INNER JOIN usuarios u ON a.usuario_id = u.id
    ORDER BY a.timestamp_accion DESC
    LIMIT ? OFFSET ?
  `,
};

module.exports = AUDITORIA;
