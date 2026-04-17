// src/routes/citas.routes.js

const router   = require('express').Router();
const ctrl     = require('../controllers/citas.controller');
const auth     = require('../middlewares/auth.middleware');
const roles    = require('../middlewares/roles.middleware');
const validate = require('../middlewares/validate.middleware');
const {
  agendarRules, cancelarRules, reasignarRules,
  citasDiariasRules, citasRangoRules,
} = require('./validators/citas.validators');

// Agendar cita (paciente, recepción, administrador)
router.post('/',
  auth,
  roles('paciente', 'recepcion', 'administrador'),
  agendarRules,
  validate,
  ctrl.agendar,
);

// Cancelar cita
router.patch('/:id/cancelar',
  auth,
  roles('paciente', 'recepcion', 'administrador'),
  cancelarRules,
  validate,
  ctrl.cancelar,
);

// Reasignar cita (solo recepción y administrador)
router.patch('/:id/reasignar',
  auth,
  roles('recepcion', 'administrador'),
  reasignarRules,
  validate,
  ctrl.reasignar,
);

// Historial del paciente autenticado
router.get('/mis-citas',
  auth,
  roles('paciente'),
  ctrl.misCitas,
);

// Citas diarias del médico autenticado
router.get('/diarias',
  auth,
  roles('medico'),
  citasDiariasRules,
  validate,
  ctrl.citasDiarias,
);

// Citas en rango (semanal/mensual) del médico autenticado
router.get('/rango',
  auth,
  roles('medico'),
  citasRangoRules,
  validate,
  ctrl.citasRango,
);

module.exports = router;
