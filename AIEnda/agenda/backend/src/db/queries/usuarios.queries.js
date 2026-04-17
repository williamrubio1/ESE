// src/db/queries/usuarios.queries.js
// Consultas SQL relacionadas con la tabla `usuarios`.

const USUARIOS = {
  BUSCAR_POR_ID: `
    SELECT id, nombre, rol_id, email, telefono, contrasena, fecha_nacimiento,
           primer_login, created_at, updated_at
    FROM usuarios
    WHERE id = ?
    LIMIT 1
  `,

  BUSCAR_POR_EMAIL: `
    SELECT id, nombre, rol_id, email, telefono, contrasena, fecha_nacimiento,
           primer_login, created_at, updated_at
    FROM usuarios
    WHERE email = ?
    LIMIT 1
  `,

  LISTAR_TODOS: `
    SELECT u.id, u.nombre, r.nombre AS rol, u.email, u.telefono, u.created_at
    FROM usuarios u
    INNER JOIN roles r ON u.rol_id = r.id
    ORDER BY u.nombre ASC
  `,

  CREAR: `
    INSERT INTO usuarios (id, nombre, rol_id, email, telefono, contrasena, fecha_nacimiento)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `,

  ACTUALIZAR_CONTRASENA: `
    UPDATE usuarios
    SET contrasena = ?, primer_login = 0, updated_at = NOW()
    WHERE id = ?
  `,

  MARCAR_PRIMER_LOGIN_COMPLETADO: `
    UPDATE usuarios
    SET primer_login = 0, updated_at = NOW()
    WHERE id = ?
  `,

  SUSPENDER: `
    UPDATE usuarios
    SET estado = 'suspendido', updated_at = NOW()
    WHERE id = ?
  `,

  ACTIVAR: `
    UPDATE usuarios
    SET estado = 'activo', updated_at = NOW()
    WHERE id = ?
  `,

  OBTENER_CONTRASENA_ACTUAL: `
    SELECT contrasena
    FROM usuarios
    WHERE id = ?
    LIMIT 1
  `,
};

module.exports = USUARIOS;
