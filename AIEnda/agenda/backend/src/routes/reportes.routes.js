// src/routes/reportes.routes.js

const router   = require('express').Router();
const ctrl     = require('../controllers/reportes.controller');
const auth     = require('../middlewares/auth.middleware');
const roles    = require('../middlewares/roles.middleware');
const validate = require('../middlewares/validate.middleware');
const { query } = require('express-validator');

const rangoRules = [
  query('fechaInicio').isDate(),
  query('fechaFin').isDate(),
];

router.get('/por-medico',    auth, roles('administrador'), rangoRules, validate, ctrl.porMedico);
router.get('/por-sede',      auth, roles('administrador'), rangoRules, validate, ctrl.porSede);
router.get('/inasistencias', auth, roles('administrador'), rangoRules, validate, ctrl.inasistencias);
router.get('/cancelaciones', auth, roles('administrador'), rangoRules, validate, ctrl.cancelaciones);
router.get('/por-canal',     auth, roles('administrador'), rangoRules, validate, ctrl.porCanal);

module.exports = router;
