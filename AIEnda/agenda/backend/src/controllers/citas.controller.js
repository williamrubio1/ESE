// src/controllers/citas.controller.js

const citasService = require('../services/citas.service');

async function agendar(req, res) {
  try {
    const { fecha, horaInicio, medicoId, sedeId } = req.body;
    const pacienteId = req.usuario.id;
    const canal      = req.body.canal || 'plataforma_web';
    const result     = await citasService.agendarCita({
      fecha, horaInicio, medicoId, pacienteId, sedeId, canal, ip: req.ip,
    });
    res.status(201).json(result);
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}

async function cancelar(req, res) {
  try {
    await citasService.cancelarCita({
      citaId:    req.params.id,
      usuarioId: req.usuario.id,
      ip:        req.ip,
      canal:     req.body.canal || 'plataforma_web',
    });
    res.json({ mensaje: 'Cita cancelada' });
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}

async function reasignar(req, res) {
  try {
    const { nuevoMedicoId, nuevaFecha, nuevaHoraInicio } = req.body;
    await citasService.reasignarCita({
      citaId:          req.params.id,
      nuevoMedicoId,
      nuevaFecha,
      nuevaHoraInicio,
      usuarioId:       req.usuario.id,
      ip:              req.ip,
      canal:           req.body.canal || 'recepcion',
    });
    res.json({ mensaje: 'Cita reasignada' });
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}

async function misCitas(req, res) {
  try {
    const citas = await citasService.citasPorPaciente(req.usuario.id);
    res.json(citas);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}

async function citasDiarias(req, res) {
  try {
    const { fecha } = req.query;
    const citas     = await citasService.citasDiariasmedico(req.usuario.id, fecha);
    res.json(citas);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}

async function citasRango(req, res) {
  try {
    const { fechaInicio, fechaFin } = req.query;
    const citas = await citasService.citasRangoMedico(req.usuario.id, fechaInicio, fechaFin);
    res.json(citas);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}

module.exports = { agendar, cancelar, reasignar, misCitas, citasDiarias, citasRango };
