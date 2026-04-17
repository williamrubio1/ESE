// src/db/queries/especialidades.queries.js

const ESPECIALIDADES = {
  LISTAR_TODAS: `
    SELECT id, nombre
    FROM especialidades
    ORDER BY nombre ASC
  `,

  BUSCAR_POR_ID: `
    SELECT id, nombre
    FROM especialidades
    WHERE id = ?
    LIMIT 1
  `,

  CREAR: `
    INSERT INTO especialidades (nombre)
    VALUES (?)
  `,
};

module.exports = ESPECIALIDADES;
