// src/api/citas.api.js

import api from './axios';

export const agendarCitaApi    = (data)              => api.post('/citas', data);
export const cancelarCitaApi   = (id, data)          => api.patch(`/citas/${id}/cancelar`, data);
export const reasignarCitaApi  = (id, data)          => api.patch(`/citas/${id}/reasignar`, data);
export const misCitasApi       = ()                  => api.get('/citas/mis-citas');
export const citasDiariasApi   = (fecha)             => api.get('/citas/diarias', { params: { fecha } });
export const citasRangoApi     = (fechaInicio, fechaFin) =>
  api.get('/citas/rango', { params: { fechaInicio, fechaFin } });
