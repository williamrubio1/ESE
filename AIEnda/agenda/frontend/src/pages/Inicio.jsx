// src/pages/Inicio.jsx
// Página principal pública. Informa sobre el servicio de agendamiento
// y dirige al usuario al login.

import { useNavigate } from 'react-router-dom';

const pasos = [
  { numero: '1', titulo: 'Inicie sesión',      descripcion: 'Use su número de documento como usuario y su fecha de nacimiento como contraseña inicial.' },
  { numero: '2', titulo: 'Elija su cita',       descripcion: 'Seleccione la sede, la especialidad, el médico y el horario que mejor se adapte a usted.' },
  { numero: '3', titulo: 'Confirme y listo',    descripcion: 'Recibirá una confirmación por correo. Recuerde que puede cancelar con al menos 12 horas de anticipación.' },
];

const canales = [
  { icono: '🌐', label: 'Plataforma web',  descripcion: 'Desde cualquier dispositivo en agenda.mieps.co' },
  { icono: '💬', label: 'WhatsApp',        descripcion: 'Próximamente disponible' },
  { icono: '📞', label: 'Recepción',       descripcion: 'En cualquiera de nuestras sedes' },
];

export default function Inicio() {
  const navigate = useNavigate();

  return (
    <div style={estilos.pagina}>

      {/* ── Encabezado ── */}
      <header style={estilos.header}>
        <div style={estilos.headerContenido}>
          <span style={estilos.logo}>🏥 Agenda</span>
          <button style={estilos.btnHeaderLogin} onClick={() => navigate('/login')}>
            Iniciar sesión
          </button>
        </div>
      </header>

      {/* ── Hero ── */}
      <section style={estilos.hero}>
        <div style={estilos.heroTexto}>
          <p style={estilos.heroEtiqueta}>Plataforma de agendamiento médico</p>
          <h1 style={estilos.heroTitulo}>
            Agende su cita médica<br />de forma rápida y segura
          </h1>
          <p style={estilos.heroDescripcion}>
            Gestione sus citas con la EPS desde cualquier lugar, en cualquier momento.
            Sin filas, sin esperas innecesarias.
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <button style={estilos.btnPrimario} onClick={() => navigate('/login')}>
              Agendar mi cita
            </button>
            <button style={estilos.btnSecundario} onClick={() => navigate('/login')}>
              Consultar mis citas
            </button>
          </div>
        </div>
        <div style={estilos.heroImagen}>
          <div style={estilos.tarjetaDemo}>
            <div style={estilos.tarjetaDemoHeader}>📅 Próxima cita</div>
            <div style={{ padding: '16px 20px' }}>
              <p style={{ margin: '0 0 6px', fontWeight: 600, color: '#343A40' }}>Medicina General</p>
              <p style={{ margin: '0 0 4px', color: '#6C757D', fontSize: 14 }}>Dr. ejemplo · Sede Centro</p>
              <p style={{ margin: '0 0 12px', color: '#6C757D', fontSize: 14 }}>Lunes 21 de abril · 10:00 AM</p>
              <span style={estilos.badgeAgendada}>✓ Confirmada</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Cómo agendar ── */}
      <section style={estilos.seccion}>
        <h2 style={estilos.seccionTitulo}>¿Cómo agendar su cita?</h2>
        <p style={estilos.seccionSubtitulo}>Solo necesita su documento de identidad</p>
        <div style={estilos.pasoGrid}>
          {pasos.map((p) => (
            <div key={p.numero} style={estilos.pasoTarjeta}>
              <div style={estilos.pasoNumero}>{p.numero}</div>
              <h3 style={estilos.pasoTitulo}>{p.titulo}</h3>
              <p style={estilos.pasoDescripcion}>{p.descripcion}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Canales ── */}
      <section style={{ ...estilos.seccion, background: '#f8f9fa' }}>
        <h2 style={estilos.seccionTitulo}>Múltiples canales de atención</h2>
        <p style={estilos.seccionSubtitulo}>Agende por el medio que prefiera</p>
        <div style={estilos.canalGrid}>
          {canales.map((c) => (
            <div key={c.label} style={estilos.canalTarjeta}>
              <span style={{ fontSize: 36 }}>{c.icono}</span>
              <h3 style={{ margin: '10px 0 4px', fontSize: 16, color: '#343A40' }}>{c.label}</h3>
              <p style={{ margin: 0, fontSize: 14, color: '#6C757D' }}>{c.descripcion}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA final ── */}
      <section style={estilos.cta}>
        <h2 style={{ color: '#fff', fontSize: 26, marginBottom: 12 }}>
          ¿Listo para agendar su cita?
        </h2>
        <p style={{ color: 'rgba(255,255,255,0.85)', marginBottom: 24, fontSize: 16 }}>
          Ingrese con su número de documento y empiece ahora
        </p>
        <button style={estilos.btnCta} onClick={() => navigate('/login')}>
          Ingresar a la plataforma
        </button>
      </section>

      {/* ── Footer ── */}
      <footer style={estilos.footer}>
        <p style={{ margin: 0 }}>
          © {new Date().getFullYear()} Agenda — Plataforma de agendamiento médico
        </p>
      </footer>

    </div>
  );
}

// ── Estilos en línea (sin dependencias externas) ──────────────────────────
const estilos = {
  pagina: {
    fontFamily: "'Segoe UI', 'Inter', sans-serif",
    color: '#343A40',
    minHeight: '100vh',
  },
  header: {
    background: '#fff',
    borderBottom: '1px solid #e9ecef',
    position: 'sticky',
    top: 0,
    zIndex: 100,
  },
  headerContenido: {
    maxWidth: 1100,
    margin: '0 auto',
    padding: '14px 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logo: {
    fontSize: 20,
    fontWeight: 700,
    color: '#007BFF',
  },
  btnHeaderLogin: {
    background: 'transparent',
    border: '2px solid #007BFF',
    color: '#007BFF',
    padding: '8px 20px',
    borderRadius: 6,
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 14,
  },
  hero: {
    maxWidth: 1100,
    margin: '0 auto',
    padding: '64px 24px',
    display: 'flex',
    alignItems: 'center',
    gap: 48,
    flexWrap: 'wrap',
  },
  heroTexto: {
    flex: 1,
    minWidth: 280,
  },
  heroEtiqueta: {
    color: '#007BFF',
    fontWeight: 600,
    fontSize: 14,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 12,
  },
  heroTitulo: {
    fontSize: 'clamp(28px, 4vw, 42px)',
    fontWeight: 700,
    lineHeight: 1.2,
    marginBottom: 16,
    color: '#212529',
  },
  heroDescripcion: {
    fontSize: 17,
    color: '#6C757D',
    lineHeight: 1.6,
    marginBottom: 28,
  },
  heroImagen: {
    flex: '0 0 320px',
    display: 'flex',
    justifyContent: 'center',
  },
  tarjetaDemo: {
    background: '#fff',
    borderRadius: 12,
    boxShadow: '0 8px 32px rgba(0,0,0,0.10)',
    width: 280,
    overflow: 'hidden',
    border: '1px solid #e9ecef',
  },
  tarjetaDemoHeader: {
    background: '#007BFF',
    color: '#fff',
    padding: '12px 20px',
    fontWeight: 600,
    fontSize: 15,
  },
  badgeAgendada: {
    background: '#d4edda',
    color: '#155724',
    padding: '4px 10px',
    borderRadius: 20,
    fontSize: 13,
    fontWeight: 600,
  },
  btnPrimario: {
    background: '#007BFF',
    color: '#fff',
    border: 'none',
    padding: '12px 28px',
    borderRadius: 8,
    fontSize: 16,
    fontWeight: 600,
    cursor: 'pointer',
  },
  btnSecundario: {
    background: '#fff',
    color: '#007BFF',
    border: '2px solid #007BFF',
    padding: '12px 28px',
    borderRadius: 8,
    fontSize: 16,
    fontWeight: 600,
    cursor: 'pointer',
  },
  seccion: {
    padding: '64px 24px',
    textAlign: 'center',
  },
  seccionTitulo: {
    fontSize: 28,
    fontWeight: 700,
    marginBottom: 8,
    color: '#212529',
  },
  seccionSubtitulo: {
    color: '#6C757D',
    fontSize: 16,
    marginBottom: 40,
  },
  pasoGrid: {
    display: 'flex',
    justifyContent: 'center',
    gap: 24,
    flexWrap: 'wrap',
    maxWidth: 900,
    margin: '0 auto',
  },
  pasoTarjeta: {
    flex: '1 1 220px',
    maxWidth: 260,
    background: '#fff',
    border: '1px solid #e9ecef',
    borderRadius: 12,
    padding: 24,
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
  },
  pasoNumero: {
    width: 40,
    height: 40,
    borderRadius: '50%',
    background: '#007BFF',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 700,
    fontSize: 18,
    margin: '0 auto 14px',
  },
  pasoTitulo: {
    fontSize: 16,
    fontWeight: 700,
    marginBottom: 8,
    color: '#212529',
  },
  pasoDescripcion: {
    fontSize: 14,
    color: '#6C757D',
    lineHeight: 1.6,
    margin: 0,
  },
  canalGrid: {
    display: 'flex',
    justifyContent: 'center',
    gap: 24,
    flexWrap: 'wrap',
    maxWidth: 800,
    margin: '0 auto',
  },
  canalTarjeta: {
    flex: '1 1 180px',
    maxWidth: 220,
    background: '#fff',
    borderRadius: 12,
    padding: 24,
    textAlign: 'center',
    border: '1px solid #e9ecef',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
  },
  cta: {
    background: 'linear-gradient(135deg, #007BFF 0%, #0056b3 100%)',
    padding: '64px 24px',
    textAlign: 'center',
  },
  btnCta: {
    background: '#fff',
    color: '#007BFF',
    border: 'none',
    padding: '14px 36px',
    borderRadius: 8,
    fontSize: 17,
    fontWeight: 700,
    cursor: 'pointer',
  },
  footer: {
    background: '#343A40',
    color: '#adb5bd',
    textAlign: 'center',
    padding: '20px 24px',
    fontSize: 14,
  },
};
