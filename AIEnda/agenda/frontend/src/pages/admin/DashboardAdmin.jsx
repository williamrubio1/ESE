// src/pages/admin/DashboardAdmin.jsx
// Panel principal del administrador con alerta de espacios vacíos.

import { useFetch }         from '../../hooks/useFetch';
import { espaciosVaciosApi } from '../../api/disponibilidad.api';
import SkeletonCard         from '../../components/common/SkeletonCard';
import EstadoVacio          from '../../components/common/EstadoVacio';

export default function DashboardAdmin() {
  const { data: espacios, loading, error } = useFetch(espaciosVaciosApi, [], []);

  return (
    <div>
      <h1>Panel de administrador</h1>

      {/* ── Sección: Espacios vacíos en las próximas 6 horas ── */}
      <section style={{ border: '2px solid #FFC107', borderRadius: 8, padding: 16, marginBottom: 24 }}>
        <h2 style={{ color: '#856404' }}>⚠ Espacios sin cita — próximas 6 horas</h2>

        {loading && <><SkeletonCard /><SkeletonCard /></>}
        {error   && <p style={{ color: 'red' }}>{error}</p>}
        {!loading && !error && !espacios?.length && (
          <EstadoVacio mensaje="No hay espacios vacíos en las próximas 6 horas." />
        )}

        {espacios?.map((e, i) => (
          <div key={i} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            border: '1px solid #ffeeba', background: '#fff3cd',
            padding: 12, marginBottom: 8, borderRadius: 6,
          }}>
            <div>
              <strong>{e.hora_inicio}</strong> — {e.medico} | {e.especialidad} | {e.sede}
            </div>
            <div>
              {/* Acciones: reasignar cita existente. El botón "Notificar" se habilitará en fase futura. */}
              <button>Reasignar cita</button>
              <button disabled title="Disponible en próxima fase" style={{ marginLeft: 8, opacity: 0.5 }}>
                Notificar usuarios
              </button>
            </div>
          </div>
        ))}
      </section>

      {/* Otras secciones del dashboard (reportes, médicos, usuarios) se agregan aquí */}
    </div>
  );
}
