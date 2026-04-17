// src/pages/paciente/AgendarCita.jsx
// Wizard de agendamiento: sede → especialidad → médico → fecha → hora → confirmación.

import { useState } from 'react';
import { useAsync } from '../../hooks/useAsync';
import { agendarCitaApi } from '../../api/citas.api';
import SkeletonCard from '../../components/common/SkeletonCard';
import EstadoVacio  from '../../components/common/EstadoVacio';

const PASOS = ['Sede', 'Especialidad', 'Médico', 'Fecha', 'Hora', 'Confirmación'];

export default function AgendarCita() {
  const [paso, setPaso]       = useState(0);
  const [datos, setDatos]     = useState({});
  const [exito, setExito]     = useState(false);
  const { ejecutar, loading, error } = useAsync(agendarCitaApi);

  function avanzar(campo, valor) {
    setDatos((d) => ({ ...d, [campo]: valor }));
    setPaso((p) => p + 1);
  }

  function retroceder() {
    setPaso((p) => Math.max(0, p - 1));
  }

  async function confirmar() {
    await ejecutar({
      sedeId:     datos.sedeId,
      medicoId:   datos.medicoId,
      fecha:      datos.fecha,
      horaInicio: datos.horaInicio,
      canal:      'plataforma_web',
    });
    setExito(true);
  }

  if (exito) return <p>¡Cita agendada exitosamente!</p>;

  return (
    <div>
      <h1>Agendar cita</h1>
      {/* Indicador de progreso */}
      <div>
        {PASOS.map((nombre, i) => (
          <span key={i} style={{ fontWeight: i === paso ? 'bold' : 'normal', marginRight: 12 }}>
            {i + 1}. {nombre}
          </span>
        ))}
      </div>

      {/* Cada paso renderiza su selector. Los datos reales vendrán de sus APIs correspondientes. */}
      {paso === 0 && <SeleccionarSede onSelect={(v) => avanzar('sedeId', v)} />}
      {paso === 1 && <SeleccionarEspecialidad onSelect={(v) => avanzar('especialidadId', v)} onVolver={retroceder} />}
      {paso === 2 && <SeleccionarMedico especialidadId={datos.especialidadId} onSelect={(v) => avanzar('medicoId', v)} onVolver={retroceder} />}
      {paso === 3 && <SeleccionarFecha onSelect={(v) => avanzar('fecha', v)} onVolver={retroceder} />}
      {paso === 4 && <SeleccionarHora medicoId={datos.medicoId} fecha={datos.fecha} onSelect={(v) => avanzar('horaInicio', v)} onVolver={retroceder} />}
      {paso === 5 && (
        <div>
          <h2>Resumen de la cita</h2>
          <p>Sede: {datos.sedeId} | Médico: {datos.medicoId} | Fecha: {datos.fecha} | Hora: {datos.horaInicio}</p>
          {error && <p style={{ color: 'red' }}>{error}</p>}
          <button onClick={retroceder}>Atrás</button>
          <button onClick={confirmar} disabled={loading}>
            {loading ? 'Confirmando...' : 'Confirmar cita'}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Sub-componentes de cada paso ───────────────────────────────────────────
// Cada uno es independiente y puede expandirse con su propia llamada API.

function SeleccionarSede({ onSelect }) {
  // TODO: cargar sedes desde API
  return (
    <div>
      <h2>Seleccione la sede</h2>
      <EstadoVacio mensaje="Cargando sedes..." />
    </div>
  );
}

function SeleccionarEspecialidad({ onSelect, onVolver }) {
  return (
    <div>
      <h2>Seleccione la especialidad</h2>
      <EstadoVacio mensaje="Cargando especialidades..." />
      <button onClick={onVolver}>Atrás</button>
    </div>
  );
}

function SeleccionarMedico({ especialidadId, onSelect, onVolver }) {
  return (
    <div>
      <h2>Seleccione el médico</h2>
      <SkeletonCard filas={3} />
      <button onClick={onVolver}>Atrás</button>
    </div>
  );
}

function SeleccionarFecha({ onSelect, onVolver }) {
  const [fecha, setFecha] = useState('');
  return (
    <div>
      <h2>Seleccione la fecha</h2>
      <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
      <button onClick={onVolver}>Atrás</button>
      <button onClick={() => onSelect(fecha)} disabled={!fecha}>Siguiente</button>
    </div>
  );
}

function SeleccionarHora({ medicoId, fecha, onSelect, onVolver }) {
  return (
    <div>
      <h2>Seleccione el horario</h2>
      <EstadoVacio mensaje="Cargando horarios disponibles..." />
      <button onClick={onVolver}>Atrás</button>
    </div>
  );
}
