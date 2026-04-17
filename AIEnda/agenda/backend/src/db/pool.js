// src/db/pool.js
// Pool de conexiones MySQL. Todo acceso a la BD pasa por este módulo.

const mysql = require('mysql2/promise');
const { DB } = require('../config/env');

const pool = mysql.createPool({
  host:               DB.host,
  port:               DB.port,
  user:               DB.user,
  password:           DB.password,
  database:           DB.database,
  timezone:           '-05:00',           // GMT-5 Bogotá
  waitForConnections: true,
  connectionLimit:    20,
  queueLimit:         0,
});

module.exports = pool;
