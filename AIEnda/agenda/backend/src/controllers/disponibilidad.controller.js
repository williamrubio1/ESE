// src/controllers/disponibilidad.controller.js

const cacheDisponibilidad = require('../services/cacheDisponibilidad.service');
const espaciosVaciosService = require('../services/espaciosVacios.service');

async function turnosLibres(req, res) {
  try {
    const { medicoId, fecha } = req.query;
    const turnos = await cacheDisponibilidad.obtener(medicoId, fecha);
    res.json(turnos);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}

async function espaciosVacios(req, res) {
  try {
    const espacios = await espaciosVaciosService.obtenerEspaciosVacios();
    res.json(espacios);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}

module.exports = { turnosLibres, espaciosVacios };
