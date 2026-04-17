// src/controllers/auth.controller.js

const authService = require('../services/auth.service');

async function login(req, res) {
  try {
    const { usuarioId, contrasena } = req.body;
    const ip     = req.ip;
    const canal  = req.body.canal || 'plataforma_web';
    const result = await authService.login({ usuarioId, contrasena, ip, canal });
    res.json(result);
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}

async function cambiarContrasena(req, res) {
  try {
    const { nuevaContrasena } = req.body;
    const usuarioId = req.usuario.id;
    await authService.cambiarContrasena({ usuarioId, nuevaContrasena, ip: req.ip });
    res.json({ mensaje: 'Contraseña actualizada' });
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}

async function obtenerContrasena(req, res) {
  try {
    const contrasena = await authService.obtenerContrasenaActual(req.params.id);
    res.json({ contrasena });
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}

async function recuperarContrasena(req, res) {
  try {
    const { email, canal } = req.body;
    await authService.iniciarRecuperacion({ email, canal });
    res.json({ mensaje: 'Si el correo existe, recibirá instrucciones' });
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}

module.exports = { login, cambiarContrasena, obtenerContrasena, recuperarContrasena };
