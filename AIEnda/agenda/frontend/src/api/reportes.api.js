// src/api/reportes.api.js

import api from './axios';

const params = (fi, ff) => ({ params: { fechaInicio: fi, fechaFin: ff } });

export const reportePorMedicoApi     = (fi, ff) => api.get('/reportes/por-medico',    params(fi, ff));
export const reportePorSedeApi       = (fi, ff) => api.get('/reportes/por-sede',      params(fi, ff));
export const reporteInasistenciasApi = (fi, ff) => api.get('/reportes/inasistencias', params(fi, ff));
export const reporteCancelacionesApi = (fi, ff) => api.get('/reportes/cancelaciones', params(fi, ff));
export const reportePorCanalApi      = (fi, ff) => api.get('/reportes/por-canal',     params(fi, ff));
