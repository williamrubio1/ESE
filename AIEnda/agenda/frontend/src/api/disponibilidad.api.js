// src/api/disponibilidad.api.js

import api from './axios';

export const turnosLibresApi    = (medicoId, fecha) =>
  api.get('/disponibilidad', { params: { medicoId, fecha } });

export const espaciosVaciosApi  = () => api.get('/disponibilidad/espacios-vacios');
