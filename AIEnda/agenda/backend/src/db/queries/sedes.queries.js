// src/db/queries/sedes.queries.js

const SEDES = {
  LISTAR_ACTIVAS: `
    SELECT id, nombre, direccion
    FROM sedes
    WHERE estado = 'activo'
    ORDER BY nombre ASC
  `,

  BUSCAR_POR_ID: `
    SELECT id, nombre, direccion, estado
    FROM sedes
    WHERE id = ?
    LIMIT 1
  `,

  CREAR: `
    INSERT INTO sedes (nombre, direccion, estado)
    VALUES (?, ?, 'activo')
  `,

  ACTUALIZAR: `
    UPDATE sedes
    SET nombre = ?, direccion = ?, updated_at = NOW()
    WHERE id = ?
  `,

  CAMBIAR_ESTADO: `
    UPDATE sedes
    SET estado = ?, updated_at = NOW()
    WHERE id = ?
  `,
};

module.exports = SEDES;
