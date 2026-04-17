// src/pages/medico/DashboardMedico.jsx
// Vista semanal y detalle diario del médico.

import { useState }       from 'react';
import { useFetch }       from '../../hooks/useFetch';
import { citasDiariasApi, citasRangoApi } from '../../api/citas.api';
import SkeletonCard       from '../../components/common/SkeletonCard';
import EstadoVacio        from '../../components/common/EstadoVacio';

function hoy() {
  return new Date().toISOString().split('T')[0];
}

export default function DashboardMedico() {
  const [fecha, setFecha] = useState(hoy());
  const { data: citas, loading, error } = useFetch(citasDiariasApi, [fecha], [fecha]);

  return (
    <div>
      <h1>Mi agenda</h1>
      <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />

      {loading && <><SkeletonCard /><SkeletonCard /></>}
      {error   && <p style={{ color: 'red' }}>{error}</p>}
      {!loading && !error && !citas?.length && (
        <EstadoVacio mensaje="Sin citas para este día." />
      )}
      {citas?.map((c) => (
        <div key={c.id} style={{ border: '1px solid #ddd', padding: 12, marginBottom: 8, borderRadius: 8 }}>
          <strong>{c.hora_inicio}</strong> — {c.paciente} | Estado: {c.estado}
        </div>
      ))}
    </div>
  );
}
