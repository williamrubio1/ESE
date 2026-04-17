// src/App.jsx
// Enrutador principal. Cada grupo de rutas está protegido por rol.

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import RutaProtegida    from './components/common/RutaProtegida';

// Inicio
import Inicio from './pages/Inicio';

// Auth
import Login             from './pages/auth/Login';
import CambiarContrasena from './pages/auth/CambiarContrasena';

// Paciente
import MisCitas   from './pages/paciente/MisCitas';
import AgendarCita from './pages/paciente/AgendarCita';

// Médico
import DashboardMedico from './pages/medico/DashboardMedico';

// Admin
import DashboardAdmin from './pages/admin/DashboardAdmin';

// Recepción
import Reagendamiento from './pages/recepcion/Reagendamiento';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Públicas */}
          <Route path="/"                     element={<Inicio />} />
          <Route path="/login"                element={<Login />} />
          <Route path="/cambiar-contrasena"   element={<CambiarContrasena />} />

          {/* Paciente */}
          <Route path="/paciente" element={<RutaProtegida roles={['paciente']}><MisCitas /></RutaProtegida>} />
          <Route path="/paciente/agendar" element={<RutaProtegida roles={['paciente']}><AgendarCita /></RutaProtegida>} />

          {/* Médico */}
          <Route path="/medico" element={<RutaProtegida roles={['medico']}><DashboardMedico /></RutaProtegida>} />

          {/* Administrador */}
          <Route path="/admin" element={<RutaProtegida roles={['administrador']}><DashboardAdmin /></RutaProtegida>} />

          {/* Recepción */}
          <Route path="/recepcion" element={<RutaProtegida roles={['recepcion']}><Reagendamiento /></RutaProtegida>} />

          {/* No autorizado */}
          <Route path="/no-autorizado" element={<p>No tiene permiso para acceder a esta sección.</p>} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
