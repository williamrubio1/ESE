// src/config/redis.js
// Cliente Redis (ioredis). Usado para caché de disponibilidad y rate limiting.

const Redis = require('ioredis');
const { REDIS } = require('./env');

const redis = new Redis({
  host:           REDIS.host,
  port:           REDIS.port,
  password:       REDIS.password,
  retryStrategy:  (times) => Math.min(times * 100, 3000),
});

redis.on('connect', () => console.log('[Redis] Conectado'));
redis.on('error',   (err) => console.error('[Redis] Error:', err.message));

module.exports = redis;
