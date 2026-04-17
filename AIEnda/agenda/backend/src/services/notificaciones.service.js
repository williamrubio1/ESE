// src/services/notificaciones.service.js
// Canal de notificaciones desacoplado. Fase inicial: solo email.
// Los métodos para WhatsApp y n8n están preparados para implementación futura.

const nodemailer = require('nodemailer');
const { MAIL }   = require('../config/env');

// ── Transporte de correo ───────────────────────────────────────────────────
const transporter = nodemailer.createTransport({
  host:   MAIL.host,
  port:   MAIL.port,
  secure: false,
  auth:   { user: MAIL.user, pass: MAIL.password },
});

// ── Helpers internos ───────────────────────────────────────────────────────
async function enviarCorreo({ to, subject, text, html }) {
  await transporter.sendMail({ from: MAIL.from, to, subject, text, html });
}

// ── Recuperación de contraseña ─────────────────────────────────────────────
async function enviarRecuperacionEmail(usuario) {
  // TODO: generar token con expiración y enlace real
  await enviarCorreo({
    to:      usuario.email,
    subject: 'Recuperación de contraseña - Agenda',
    text:    `Hola ${usuario.nombre}, su contraseña actual es: ${usuario.contrasena}`,
  });
}

// Preparado para fase futura
async function enviarRecuperacionWhatsapp(usuario) {
  // TODO: integrar con n8n/WhatsApp Business API
  throw new Error('Canal WhatsApp no implementado aún');
}

async function enviarRecuperacionN8n(usuario) {
  // TODO: llamada webhook a n8n
  throw new Error('Canal n8n no implementado aún');
}

// ── Notificación de cita agendada ──────────────────────────────────────────
async function notificarCitaAgendada({ email, nombre, fecha, horaInicio, medico, sede, canal }) {
  if (canal === 'plataforma_web' || canal === 'recepcion') {
    await enviarCorreo({
      to:      email,
      subject: 'Cita médica confirmada - Agenda',
      text:    `Hola ${nombre}, su cita con ${medico} en ${sede} está confirmada para el ${fecha} a las ${horaInicio}.`,
    });
  }
  // WhatsApp/n8n: pendiente implementación futura
}

// ── Notificación de cancelación ────────────────────────────────────────────
async function notificarCancelacion({ email, nombre, fecha, horaInicio }) {
  await enviarCorreo({
    to:      email,
    subject: 'Cita cancelada - Agenda',
    text:    `Hola ${nombre}, su cita del ${fecha} a las ${horaInicio} ha sido cancelada.`,
  });
}

// ── Alerta de espacio vacío (para futura notificación masiva) ──────────────
async function notificarEspacioDisponible({ canal, turno }) {
  // TODO: implementar cuando esté listo el módulo de pre-asignación
  // canal: plataforma_web | whatsapp | n8n
  console.log('[Notificaciones] Espacio disponible pendiente de notificar:', turno);
}

module.exports = {
  enviarRecuperacionEmail,
  enviarRecuperacionWhatsapp,
  enviarRecuperacionN8n,
  notificarCitaAgendada,
  notificarCancelacion,
  notificarEspacioDisponible,
};
