// src/middlewares/loginRateLimit.middleware.js
// Controla intentos de login por usuario: máx. 5 intentos, bloqueo de 10 minutos.
// El conteo se almacena en Redis con clave: login_attempts:{usuarioId}

const redis = require('../config/redis');

const MAX_INTENTOS   = 5;
const BLOQUEO_SEG    = 10 * 60; // 10 minutos en segundos
const CLAVE_PREFIX   = 'login_attempts:';
const BLOQUEO_PREFIX = 'login_blocked:';

async function incrementarIntentos(usuarioId) {
  const clave = `${CLAVE_PREFIX}${usuarioId}`;
  const intentos = await redis.incr(clave);
  if (intentos === 1) {
    // Primera vez: establece el TTL de la ventana de conteo
    await redis.expire(clave, BLOQUEO_SEG);
  }
  return intentos;
}

async function bloquearUsuario(usuarioId) {
  const clave = `${BLOQUEO_PREFIX}${usuarioId}`;
  await redis.set(clave, '1', 'EX', BLOQUEO_SEG);
}

async function estaBloquado(usuarioId) {
  const clave = `${BLOQUEO_PREFIX}${usuarioId}`;
  const val = await redis.get(clave);
  return val !== null;
}

async function resetearIntentos(usuarioId) {
  await redis.del(`${CLAVE_PREFIX}${usuarioId}`);
  await redis.del(`${BLOQUEO_PREFIX}${usuarioId}`);
}

// Middleware que se aplica en el endpoint POST /auth/login
async function loginRateLimitMiddleware(req, res, next) {
  const { usuarioId } = req.body;
  if (!usuarioId) return next();

  const bloqueado = await estaBloquado(usuarioId);
  if (bloqueado) {
    return res.status(429).json({
      error: 'Usuario bloqueado por múltiples intentos fallidos. Intente en 10 minutos.',
    });
  }
  next();
}

module.exports = {
  loginRateLimitMiddleware,
  incrementarIntentos,
  bloquearUsuario,
  resetearIntentos,
  MAX_INTENTOS,
};
