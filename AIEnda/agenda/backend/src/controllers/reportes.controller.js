// src/controllers/reportes.controller.js

const reportesService = require('../services/reportes.service');

async function porMedico(req, res) {
  try {
    const { fechaInicio, fechaFin } = req.query;
    res.json(await reportesService.ocupacionPorMedico(fechaInicio, fechaFin));
  } catch (err) { res.status(500).json({ error: err.message }); }
}

async function porSede(req, res) {
  try {
    const { fechaInicio, fechaFin } = req.query;
    res.json(await reportesService.ocupacionPorSede(fechaInicio, fechaFin));
  } catch (err) { res.status(500).json({ error: err.message }); }
}

async function inasistencias(req, res) {
  try {
    const { fechaInicio, fechaFin } = req.query;
    res.json(await reportesService.inasistencias(fechaInicio, fechaFin));
  } catch (err) { res.status(500).json({ error: err.message }); }
}

async function cancelaciones(req, res) {
  try {
    const { fechaInicio, fechaFin } = req.query;
    res.json(await reportesService.cancelaciones(fechaInicio, fechaFin));
  } catch (err) { res.status(500).json({ error: err.message }); }
}

async function porCanal(req, res) {
  try {
    const { fechaInicio, fechaFin } = req.query;
    res.json(await reportesService.citasPorCanal(fechaInicio, fechaFin));
  } catch (err) { res.status(500).json({ error: err.message }); }
}

module.exports = { porMedico, porSede, inasistencias, cancelaciones, porCanal };
