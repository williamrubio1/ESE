// src/routes/auth.routes.js

const router  = require('express').Router();
const ctrl    = require('../controllers/auth.controller');
const auth    = require('../middlewares/auth.middleware');
const roles   = require('../middlewares/roles.middleware');
const validate = require('../middlewares/validate.middleware');
const { loginRateLimitMiddleware } = require('../middlewares/loginRateLimit.middleware');
const {
  loginRules,
  cambiarContrasenaRules,
  recuperarRules,
  obtenerContrasenaRules,
} = require('./validators/auth.validators');

// POST /api/auth/login
router.post('/login',
  loginRateLimitMiddleware,
  loginRules,
  validate,
  ctrl.login,
);

// POST /api/auth/cambiar-contrasena  (usuario autenticado)
router.post('/cambiar-contrasena',
  auth,
  cambiarContrasenaRules,
  validate,
  ctrl.cambiarContrasena,
);

// POST /api/auth/recuperar
router.post('/recuperar',
  recuperarRules,
  validate,
  ctrl.recuperarContrasena,
);

// GET /api/auth/contrasena/:id  (solo admin)
router.get('/contrasena/:id',
  auth,
  roles('administrador'),
  obtenerContrasenaRules,
  validate,
  ctrl.obtenerContrasena,
);

module.exports = router;
