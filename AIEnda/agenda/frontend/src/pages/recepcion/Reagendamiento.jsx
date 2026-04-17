// src/pages/recepcion/Reagendamiento.jsx
// Pantalla única compacta para reagendamiento: buscar → ver cita → nuevo horario → confirmar.

import { useState }       from 'react';
import { useAsync }       from '../../hooks/useAsync';
import { reasignarCitaApi } from '../../api/citas.api';
import EstadoVacio        from '../../components/common/EstadoVacio';

export default function Reagendamiento() {
  const [busqueda, setBusqueda]       = useState('');
  const [citaSeleccionada, setCita]   = useState(null);
  const [nuevoHorario, setNuevoHorario] = useState({ medicoId: '', fecha: '', horaInicio: '' });
  const [exito, setExito]             = useState(false);
  const { ejecutar, loading, error }  = useAsync(reasignarCitaApi);

  async function confirmar(e) {
    e.preventDefault();
    await ejecutar(citaSeleccionada.id, {
      nuevoMedicoId:   nuevoHorario.medicoId,
      nuevaFecha:      nuevoHorario.fecha,
      nuevaHoraInicio: nuevoHorario.horaInicio,
      canal:           'recepcion',
    });
    setExito(true);
  }

  if (exito) return <p>Cita reasignada exitosamente.</p>;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>

      {/* ── Columna izquierda: Búsqueda y cita actual ── */}
      <div>
        <h2>Buscar cita</h2>
        <input
          placeholder="Nombre, ID de paciente o fecha"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          style={{ width: '100%', padding: 8, marginBottom: 12 }}
        />
        {/* TODO: mostrar resultados de búsqueda desde API */}
        {!citaSeleccionada && <EstadoVacio mensaje="Ingrese un criterio de búsqueda." />}

        {citaSeleccionada && (
          <div style={{ border: '1px solid #007BFF', borderRadius: 8, padding: 12 }}>
            <h3>Cita actual</h3>
            <p><strong>Paciente:</strong> {citaSeleccionada.paciente}</p>
            <p><strong>Médico:</strong> {citaSeleccionada.medico}</p>
            <p><strong>Fecha:</strong> {citaSeleccionada.fecha} {citaSeleccionada.hora_inicio}</p>
            <p><strong>Estado:</strong> {citaSeleccionada.estado}</p>
          </div>
        )}
      </div>

      {/* ── Columna derecha: Nuevo horario ── */}
      <div>
        <h2>Nuevo horario</h2>
        {!citaSeleccionada
          ? <EstadoVacio mensaje="Seleccione una cita para reagendar." />
          : (
            <form onSubmit={confirmar}>
              <div>
                <label>Médico</label>
                {/* TODO: cargar lista de médicos desde API */}
                <input
                  placeholder="ID del médico"
                  value={nuevoHorario.medicoId}
                  onChange={(e) => setNuevoHorario((h) => ({ ...h, medicoId: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label>Fecha</label>
                <input
                  type="date"
                  value={nuevoHorario.fecha}
                  onChange={(e) => setNuevoHorario((h) => ({ ...h, fecha: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label>Hora</label>
                {/* TODO: mostrar horarios disponibles desde cacheDisponibilidad */}
                <input
                  type="time"
                  step="1200"
                  value={nuevoHorario.horaInicio}
                  onChange={(e) => setNuevoHorario((h) => ({ ...h, horaInicio: e.target.value }))}
                  required
                />
              </div>
              {error && <p style={{ color: 'red' }}>{error}</p>}
              <button type="submit" disabled={loading} style={{ marginTop: 16, width: '100%' }}>
                {loading ? 'Confirmando...' : 'Confirmar reagendamiento'}
              </button>
            </form>
          )
        }
      </div>

    </div>
  );
}
