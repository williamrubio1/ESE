// src/middlewares/validate.middleware.js
// Ejecuta las reglas de express-validator y responde con errores si los hay.

const { validationResult } = require('express-validator');

function validateMiddleware(req, res, next) {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(422).json({ errores: errors.array() });
  }
  next();
}

module.exports = validateMiddleware;
