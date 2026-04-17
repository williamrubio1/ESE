// src/config/env.js
// Carga y valida las variables de entorno.
// Todas las partes del sistema importan desde aquí, nunca de process.env directamente.

require('dotenv').config();

const required = [
  'JWT_SECRET',
  'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME',
  'REDIS_HOST',
];

required.forEach((key) => {
  if (!process.env[key]) {
    throw new Error(`Variable de entorno requerida no definida: ${key}`);
  }
});

module.exports = {
  // Servidor
  PORT: parseInt(process.env.PORT, 10) || 3001,
  NODE_ENV: process.env.NODE_ENV || 'development',

  // JWT
  JWT_SECRET: process.env.JWT_SECRET,
  JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || '8h',

  // Base de datos
  DB: {
    host:     process.env.DB_HOST,
    port:     parseInt(process.env.DB_PORT, 10) || 3306,
    user:     process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME,
  },

  // Redis
  REDIS: {
    host:     process.env.REDIS_HOST,
    port:     parseInt(process.env.REDIS_PORT, 10) || 6379,
    password: process.env.REDIS_PASSWORD || undefined,
  },

  // Correo
  MAIL: {
    host:     process.env.MAIL_HOST,
    port:     parseInt(process.env.MAIL_PORT, 10) || 587,
    user:     process.env.MAIL_USER,
    password: process.env.MAIL_PASSWORD,
    from:     process.env.MAIL_FROM,
  },
};
