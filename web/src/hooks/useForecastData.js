import { useState, useEffect, useCallback } from 'react';
import { getForecasts, getPVForecast, getDemandForecast, getRiskAssessment } from '../api/kora';

export function useForecastData(siteId = 'mahavelona', hours = 24) {
  const [pvForecast, setPvForecast] = useState([]);
  const [demandForecast, setDemandForecast] = useState([]);
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getForecasts(siteId, hours);

      // Debug logging
      console.log('[useForecastData] raw data:', data);

      // Extract arrays from API response
      // PV API returns: { pvKw: [...], ... }
      // Demand API returns: { demandKw: [...], ... }
      const pvArray = data.pv?.pvKw || data.pv?.pvKwArray || [];
      const demandArray = data.demand?.demandKw || data.demand?.demandKwArray || [];

      console.log('[useForecastData] pvArray:', pvArray);
      console.log('[useForecastData] demandArray:', demandArray);

      // Ensure arrays are valid
      setPvForecast(Array.isArray(pvArray) ? pvArray : []);
      setDemandForecast(Array.isArray(demandArray) ? demandArray : []);
      setRisk(data.risk);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch forecasts:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [siteId, hours]);

  useEffect(() => {
    refresh();
    // Refresh forecasts every 5 minutes
    const interval = setInterval(refresh, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [refresh]);

  return { pvForecast, demandForecast, risk, loading, error, refresh };
}

export function usePVForecast(siteId = 'mahavelona', hours = 24) {
  const [forecast, setForecast] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getPVForecast(siteId, hours)
      .then(data => {
        const pvArray = data.pvKw || data.pvKwArray || data || [];
        setForecast(Array.isArray(pvArray) ? pvArray : []);
        setError(null);
      })
      .catch(err => {
        console.error('Failed to fetch PV forecast:', err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [siteId, hours]);

  return { forecast, loading, error };
}

export function useDemandForecast(siteId = 'mahavelona', hours = 24) {
  const [forecast, setForecast] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDemandForecast(siteId, hours)
      .then(data => {
        const demandArray = data.demandKw || data.demandKwArray || data || [];
        setForecast(Array.isArray(demandArray) ? demandArray : []);
        setError(null);
      })
      .catch(err => {
        console.error('Failed to fetch demand forecast:', err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [siteId, hours]);

  return { forecast, loading, error };
}

export function useRiskAssessment(siteId = 'mahavelona') {
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getRiskAssessment(siteId)
      .then(data => {
        setRisk(data);
        setError(null);
      })
      .catch(err => {
        console.error('Failed to fetch risk assessment:', err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [siteId]);

  return { risk, loading, error };
}

export default useForecastData;
