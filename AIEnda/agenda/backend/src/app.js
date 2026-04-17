// src/app.js
// Configuración de Express: middlewares globales y montaje de rutas.

process.env.TZ = 'America/Bogota';

const express     = require('express');
const helmet      = require('helmet');
const cors        = require('cors');
const rateLimit   = require('express-rate-limit');

const authRoutes          = require('./routes/auth.routes');
const citasRoutes         = require('./routes/citas.routes');
const disponibilidadRoutes = require('./routes/disponibilidad.routes');
const reportesRoutes      = require('./routes/reportes.routes');

const app = express();

// ── Seguridad de cabeceras ──────────────────────────────────────────────────
app.use(helmet());

// ── CORS ───────────────────────────────────────────────────────────────────
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true,
}));

// ── Rate limit general de la API (no el de login, ese está en su middleware) ─
app.use('/api', rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutos
  max:      200,
  standardHeaders: true,
  legacyHeaders:   false,
  message: { error: 'Demasiadas solicitudes. Intente más tarde.' },
}));

// ── Parseo de JSON ──────────────────────────────────────────────────────────
app.use(express.json());

// ── Rutas ──────────────────────────────────────────────────────────────────
app.use('/api/auth',           authRoutes);
app.use('/api/citas',          citasRoutes);
app.use('/api/disponibilidad', disponibilidadRoutes);
app.use('/api/reportes',       reportesRoutes);

// ── Health check ───────────────────────────────────────────────────────────
app.get('/api/health', (_req, res) => res.json({ status: 'ok' }));

// ── Manejo de rutas no encontradas ─────────────────────────────────────────
app.use((_req, res) => res.status(404).json({ error: 'Ruta no encontrada' }));

module.exports = app;
