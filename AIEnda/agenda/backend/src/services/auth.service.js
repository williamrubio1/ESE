// src/services/auth.service.js
// Lógica de autenticación: login, cambio de contraseña, recuperación.

const pool     = require('../db/pool');
const USUARIOS = require('../db/queries/usuarios.queries');
const { generarToken }       = require('../utils/jwt');
const { registrarAuditoria } = require('../utils/auditoria');
const {
  loginRateLimitMiddleware,
  incrementarIntentos,
  bloquearUsuario,
  resetearIntentos,
  MAX_INTENTOS,
} = require('../middlewares/loginRateLimit.middleware');

/**
 * Inicia sesión. La contraseña se compara en texto plano (almacenada así en BD).
 * @returns {{ token, primerLogin }}
 */
async function login({ usuarioId, contrasena, ip, canal = 'plataforma_web' }) {
  const [rows] = await pool.execute(USUARIOS.BUSCAR_POR_ID, [usuarioId]);
  const usuario = rows[0];

  if (!usuario || usuario.contrasena !== contrasena) {
    // Incrementar contador de intentos fallidos
    const intentos = await incrementarIntentos(usuarioId);
    if (intentos >= MAX_INTENTOS) {
      await bloquearUsuario(usuarioId);
    }
    const error = new Error('Credenciales incorrectas');
    error.status = 401;
    throw error;
  }

  // Login exitoso: limpiar contadores
  await resetearIntentos(usuarioId);

  await registrarAuditoria({
    usuarioId: usuario.id,
    accion:    'login',
    entidad:   'usuarios',
    entidadId: usuario.id,
    detalle:   'Inicio de sesión exitoso',
    canal,
    ip,
  });

  const token = generarToken({
    id:  usuario.id,
    rol: usuario.rol_id,
  });

  return { token, primerLogin: !!usuario.primer_login };
}

/**
 * Cambia la contraseña de un usuario.
 */
async function cambiarContrasena({ usuarioId, nuevaContrasena, ip, canal = 'plataforma_web' }) {
  await pool.execute(USUARIOS.ACTUALIZAR_CONTRASENA, [nuevaContrasena, usuarioId]);

  await registrarAuditoria({
    usuarioId,
    accion:    'cambio_contrasena',
    entidad:   'usuarios',
    entidadId: usuarioId,
    detalle:   'Contraseña actualizada',
    canal,
    ip,
  });
}

/**
 * Retorna la contraseña actual de un usuario (para soporte/administración).
 */
async function obtenerContrasenaActual(usuarioId) {
  const [rows] = await pool.execute(USUARIOS.OBTENER_CONTRASENA_ACTUAL, [usuarioId]);
  if (!rows[0]) {
    const err = new Error('Usuario no encontrado'); err.status = 404; throw err;
  }
  return rows[0].contrasena;
}

/**
 * Inicia el flujo de recuperación de contraseña.
 * Canal inicial: correo. Arquitectura abierta para WhatsApp/n8n.
 * @param {string} canal - 'email' | 'whatsapp' | 'n8n'
 */
async function iniciarRecuperacion({ email, canal = 'email' }) {
  const [rows] = await pool.execute(USUARIOS.BUSCAR_POR_EMAIL, [email]);
  const usuario = rows[0];

  // Siempre responder igual para no filtrar si el email existe
  if (!usuario) return;

  // El canal determina el servicio que entrega el mensaje
  const canales = {
    email:    () => require('./notificaciones.service').enviarRecuperacionEmail(usuario),
    whatsapp: () => require('./notificaciones.service').enviarRecuperacionWhatsapp(usuario),
    n8n:      () => require('./notificaciones.service').enviarRecuperacionN8n(usuario),
  };

  const enviar = canales[canal];
  if (enviar) await enviar();
}

module.exports = { login, cambiarContrasena, obtenerContrasenaActual, iniciarRecuperacion };
