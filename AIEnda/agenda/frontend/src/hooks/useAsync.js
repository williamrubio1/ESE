// src/hooks/useAsync.js
// Hook para operaciones manuales (submit, cancel, etc.) con estado de carga y error.

import { useState, useCallback } from 'react';

export function useAsync(apiFn) {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const ejecutar = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFn(...args);
      return res.data;
    } catch (err) {
      const msg = err.response?.data?.error || 'Error inesperado';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  }, [apiFn]);

  return { ejecutar, loading, error };
}
