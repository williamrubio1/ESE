-- ============================================================
--  Agenda — Base de datos
--  Zona horaria: America/Bogota (GMT-5)
--  Motor: MySQL 8.x
--  Ejecutar en orden; cada sección está separada para editarse
--  de forma independiente.
-- ============================================================

SET NAMES utf8mb4;
SET time_zone = '-05:00';

CREATE DATABASE IF NOT EXISTS agenda
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE agenda;

-- ============================================================
-- 1. ROLES
-- ============================================================
CREATE TABLE IF NOT EXISTS roles (
  id     TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(30)      NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_roles_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO roles (nombre) VALUES
  ('paciente'),
  ('medico'),
  ('administrador'),
  ('recepcion');

-- ============================================================
-- 2. ESPECIALIDADES
-- ============================================================
CREATE TABLE IF NOT EXISTS especialidades (
  id     SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100)      NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_especialidades_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 3. SEDES
-- ============================================================
CREATE TABLE IF NOT EXISTS sedes (
  id         SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre     VARCHAR(100)      NOT NULL,
  direccion  VARCHAR(200)      NOT NULL,
  estado     ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
  created_at DATETIME NOT NULL DEFAULT NOW(),
  updated_at DATETIME NOT NULL DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 4. USUARIOS
-- Contraseña almacenada en texto plano (acceso administrado
-- directamente en BD). Campo primer_login controla el flujo
-- de cambio obligatorio en el primer acceso.
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
  id               VARCHAR(20)       NOT NULL,   -- ID del documento / usuario
  nombre           VARCHAR(120)      NOT NULL,
  rol_id           TINYINT UNSIGNED  NOT NULL,
  email            VARCHAR(150)      NOT NULL,
  telefono         VARCHAR(25)       NOT NULL,
  indicativo_pais  VARCHAR(6)        NOT NULL DEFAULT '+57',
  contrasena       VARCHAR(100)      NOT NULL,   -- texto plano (ver especificaciones)
  fecha_nacimiento DATE              NOT NULL,
  primer_login     TINYINT(1)        NOT NULL DEFAULT 1,
  estado           ENUM('activo','suspendido') NOT NULL DEFAULT 'activo',
  created_at       DATETIME NOT NULL DEFAULT NOW(),
  updated_at       DATETIME NOT NULL DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id),
  UNIQUE  KEY uq_usuarios_email (email),
  FOREIGN KEY fk_usuarios_rol (rol_id) REFERENCES roles (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 5. MÉDICOS
-- ruta_foto: reservado para fase futura (hoy se usan avatares)
-- ============================================================
CREATE TABLE IF NOT EXISTS medicos (
  id              INT UNSIGNED      NOT NULL AUTO_INCREMENT,
  nombre          VARCHAR(120)      NOT NULL,
  especialidad_id SMALLINT UNSIGNED NOT NULL,
  sede_id         SMALLINT UNSIGNED NOT NULL,
  disponibilidad  JSON              NULL,    -- estructura de horarios semanales
  estado          ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
  ruta_foto       VARCHAR(255)      NULL,    -- reservado fase futura
  created_at      DATETIME NOT NULL DEFAULT NOW(),
  updated_at      DATETIME NOT NULL DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id),
  FOREIGN KEY fk_medicos_especialidad (especialidad_id) REFERENCES especialidades (id),
  FOREIGN KEY fk_medicos_sede         (sede_id)         REFERENCES sedes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 6. TURNOS DISPONIBLES
-- Bloques de 20 minutos generados por la disponibilidad del médico.
-- La disponibilidad del médico es la raíz del sistema.
-- ============================================================
CREATE TABLE IF NOT EXISTS turnos_disponibles (
  id          INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  medico_id   INT UNSIGNED     NOT NULL,
  fecha       DATE             NOT NULL,
  hora_inicio TIME             NOT NULL,
  hora_fin    TIME             NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_turno (medico_id, fecha, hora_inicio),
  KEY idx_turno_fecha (fecha),
  FOREIGN KEY fk_turno_medico (medico_id) REFERENCES medicos (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 7. CITAS
-- canal: origen del agendamiento (para auditoría y reportes)
-- ============================================================
CREATE TABLE IF NOT EXISTS citas (
  id          INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  fecha       DATE             NOT NULL,
  hora_inicio TIME             NOT NULL,
  hora_fin    TIME             NOT NULL,
  estado      ENUM(
                'agendada',
                'confirmada',
                'atendida',
                'cancelada',
                'inasistencia'
              ) NOT NULL DEFAULT 'agendada',
  canal       ENUM(
                'plataforma_web',
                'whatsapp',
                'n8n',
                'recepcion',
                'administrador'
              ) NOT NULL DEFAULT 'plataforma_web',
  paciente_id VARCHAR(20)      NOT NULL,
  medico_id   INT UNSIGNED     NOT NULL,
  sede_id     SMALLINT UNSIGNED NOT NULL,
  created_at  DATETIME NOT NULL DEFAULT NOW(),
  updated_at  DATETIME NOT NULL DEFAULT NOW() ON UPDATE NOW(),
  PRIMARY KEY (id),
  -- Índice principal para consultas de disponibilidad
  KEY idx_citas_medico_fecha_estado (medico_id, fecha, estado),
  KEY idx_citas_paciente            (paciente_id),
  KEY idx_citas_sede_fecha          (sede_id, fecha),
  FOREIGN KEY fk_citas_paciente (paciente_id) REFERENCES usuarios (id),
  FOREIGN KEY fk_citas_medico   (medico_id)   REFERENCES medicos  (id),
  FOREIGN KEY fk_citas_sede     (sede_id)     REFERENCES sedes    (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 8. AUDITORÍA
-- Registra todas las acciones críticas del sistema.
-- canal: medio por el cual se realizó la acción.
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria (
  id               BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  usuario_id       VARCHAR(20)      NOT NULL,
  accion           ENUM(
                     'login',
                     'cambio_contrasena',
                     'agendar_cita',
                     'cancelar_cita',
                     'reasignar_cita'
                   ) NOT NULL,
  entidad          VARCHAR(50)      NOT NULL,
  entidad_id       INT              NULL,
  detalle          VARCHAR(255)     NOT NULL DEFAULT '',
  canal            ENUM(
                     'plataforma_web',
                     'whatsapp',
                     'n8n',
                     'recepcion',
                     'administrador'
                   ) NOT NULL DEFAULT 'plataforma_web',
  ip               VARCHAR(45)      NOT NULL DEFAULT '',
  timestamp_accion DATETIME         NOT NULL DEFAULT NOW(),
  PRIMARY KEY (id),
  KEY idx_auditoria_usuario_accion (usuario_id, accion, timestamp_accion),
  -- Sin FK a usuarios: la auditoría debe sobrevivir aunque el usuario sea eliminado
  KEY idx_auditoria_timestamp (timestamp_accion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- FIN DEL ESQUEMA
-- ============================================================
