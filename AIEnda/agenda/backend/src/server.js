// src/server.js
// Punto de entrada. Levanta el servidor y verifica conexiones.

const app   = require('./app');
const pool  = require('./db/pool');
const redis = require('./config/redis');
const { PORT } = require('./config/env');

async function iniciar() {
  // Verificar conexión a MySQL
  try {
    const conn = await pool.getConnection();
    await conn.execute("SET time_zone = '-05:00'");
    conn.release();
    console.log('[MySQL] Conectado');
  } catch (err) {
    console.error('[MySQL] Error de conexión:', err.message);
    process.exit(1);
  }

  // Redis ya se auto-conecta en config/redis.js

  app.listen(PORT, () => {
    console.log(`[Servidor] Escuchando en puerto ${PORT} | TZ: ${process.env.TZ}`);
  });
}

iniciar();
