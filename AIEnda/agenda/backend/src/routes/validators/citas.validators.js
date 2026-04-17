// src/routes/validators/citas.validators.js

const { body, param, query } = require('express-validator');

const agendarRules = [
  body('fecha').isDate().withMessage('fecha inválida (YYYY-MM-DD)'),
  body('horaInicio').matches(/^\d{2}:\d{2}$/).withMessage('horaInicio inválida (HH:MM)'),
  body('medicoId').isInt({ min: 1 }),
  body('sedeId').isInt({ min: 1 }),
  body('canal').optional().isIn(['plataforma_web', 'whatsapp', 'n8n', 'recepcion', 'administrador']),
];

const cancelarRules = [
  param('id').isInt({ min: 1 }),
];

const reasignarRules = [
  param('id').isInt({ min: 1 }),
  body('nuevoMedicoId').isInt({ min: 1 }),
  body('nuevaFecha').isDate(),
  body('nuevaHoraInicio').matches(/^\d{2}:\d{2}$/),
];

const citasDiariasRules = [
  query('fecha').isDate(),
];

const citasRangoRules = [
  query('fechaInicio').isDate(),
  query('fechaFin').isDate(),
];

module.exports = { agendarRules, cancelarRules, reasignarRules, citasDiariasRules, citasRangoRules };
