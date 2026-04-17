// src/routes/validators/auth.validators.js

const { body, param } = require('express-validator');

const loginRules = [
  body('usuarioId').notEmpty().withMessage('usuarioId requerido'),
  body('contrasena').notEmpty().withMessage('contrasena requerida'),
];

const cambiarContrasenaRules = [
  body('nuevaContrasena')
    .notEmpty()
    .isLength({ min: 6 })
    .withMessage('La contraseña debe tener al menos 6 caracteres'),
];

const recuperarRules = [
  body('email').isEmail().withMessage('Email inválido'),
  body('canal').optional().isIn(['email', 'whatsapp', 'n8n']),
];

const obtenerContrasenaRules = [
  param('id').notEmpty().withMessage('id requerido'),
];

module.exports = { loginRules, cambiarContrasenaRules, recuperarRules, obtenerContrasenaRules };
