// src/pages/paciente/MisCitas.jsx

import { useFetch }      from '../../hooks/useFetch';
import { misCitasApi }   from '../../api/citas.api';
import { useAsync }      from '../../hooks/useAsync';
import { cancelarCitaApi } from '../../api/citas.api';
import SkeletonCard      from '../../components/common/SkeletonCard';
import EstadoVacio       from '../../components/common/EstadoVacio';

export default function MisCitas() {
  const { data: citas, loading, error, refetch } = useFetch(misCitasApi, [], []);
  const { ejecutar: cancelar, loading: cancelando } = useAsync(cancelarCitaApi);

  async function handleCancelar(id) {
    await cancelar(id, { canal: 'plataforma_web' });
    refetch();
  }

  if (loading) return <><SkeletonCard /><SkeletonCard /><SkeletonCard /></>;
  if (error)   return <p style={{ color: 'red' }}>{error}</p>;
  if (!citas?.length) return <EstadoVacio mensaje="No tienes citas agendadas." />;

  return (
    <div>
      <h1>Mis citas</h1>
      {citas.map((c) => (
        <div key={c.id} style={{ border: '1px solid #ddd', padding: 12, marginBottom: 8, borderRadius: 8 }}>
          <strong>{c.fecha} {c.hora_inicio}</strong> — {c.medico} | {c.especialidad} | {c.sede}
          <br />Estado: {c.estado}
          {c.estado === 'agendada' && (
            <button onClick={() => handleCancelar(c.id)} disabled={cancelando} style={{ marginLeft: 12 }}>
              Cancelar
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
