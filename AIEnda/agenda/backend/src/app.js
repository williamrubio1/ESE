// src/app.js
// Configuración de Express: middlewares globales y montaje de rutas.

process.env.TZ = 'America/Bogota';

const path        = require('path');
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

// ── CORS (solo activo en desarrollo; en prod el mismo Express sirve el front) ─
if (process.env.NODE_ENV !== 'production') {
  app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true,
  }));
}

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

// ── Frontend estático (build de React) ─────────────────────────────────────
// En producción Hostinger, el build de React se copia a backend/public/
const frontendBuild = path.join(__dirname, '..', 'public');
app.use(express.static(frontendBuild));

// Cualquier ruta que no sea /api/* devuelve index.html (SPA)
app.get(/^(?!\/api).*/, (_req, res) => {
  res.sendFile(path.join(frontendBuild, 'index.html'));
});

// ── Manejo de rutas de API no encontradas ──────────────────────────────────
app.use((_req, res) => res.status(404).json({ error: 'Ruta no encontrada' }));

module.exports = app;
