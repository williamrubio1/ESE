// src/hooks/useFetch.js
// Hook genérico para llamadas a la API con estado de carga y error.

import { useState, useEffect, useCallback } from 'react';

export function useFetch(apiFn, params = [], deps = []) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const ejecutar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFn(...params);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Error inesperado');
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { ejecutar(); }, [ejecutar]);

  return { data, loading, error, refetch: ejecutar };
}
