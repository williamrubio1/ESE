// src/middlewares/roles.middleware.js
// Restringe el acceso a rutas según el rol del usuario autenticado.
// Uso: rolesMiddleware('admin', 'recepcion')

function rolesMiddleware(...rolesPermitidos) {
  return (req, res, next) => {
    if (!req.usuario) {
      return res.status(401).json({ error: 'No autenticado' });
    }
    if (!rolesPermitidos.includes(req.usuario.rol)) {
      return res.status(403).json({ error: 'Acceso no autorizado para este rol' });
    }
    next();
  };
}

module.exports = rolesMiddleware;
