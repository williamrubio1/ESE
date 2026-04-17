// src/api/auth.api.js

import api from './axios';

export const loginApi              = (data)  => api.post('/auth/login', data);
export const cambiarContrasenaApi  = (data)  => api.post('/auth/cambiar-contrasena', data);
export const recuperarContrasenaApi = (data) => api.post('/auth/recuperar', data);
export const obtenerContrasenaApi  = (id)    => api.get(`/auth/contrasena/${id}`);
