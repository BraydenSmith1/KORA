import { useState, useEffect, useCallback } from 'react';
import { getOptimizerStatus, subscribeToOptimizer, getOptimizerHistory } from '../api/kora';

export function useOptimizerData(siteId = 'mahavelona') {
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connected, setConnected] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, historyRes] = await Promise.all([
        getOptimizerStatus(siteId),
        getOptimizerHistory(siteId, 168) // 7 days of hourly data
      ]);

      // Debug logging
      console.log('[useOptimizerData] statusRes:', statusRes);
      console.log('[useOptimizerData] historyRes:', historyRes);

      // Extract simulation state from the response
      // API returns: { simulation: {...}, latestRun: {...}, telemetry: [...] }
      const simState = statusRes.simulation || statusRes;
      const latestRun = statusRes.latestRun;
      const telemetry = statusRes.telemetry || [];

      setStatus({
        ...simState,
        latestRun,
        telemetry,
        // Ensure we have defaults
        isRunning: simState.isRunning ?? false,
        isPaused: simState.isPaused ?? false,
        batterySocPct: simState.batterySocPct ?? 50,
        currentPvKw: simState.currentPvKw ?? 0,
        currentDemandKw: simState.currentDemandKw ?? 0,
        currentPriceAriary: simState.currentPriceAriary ?? 1850,
        totalRevenueAr: simState.totalRevenueAr ?? 0,
        totalCurtailKwh: simState.totalCurtailKwh ?? 0,
      });

      // Extract runs array from history response
      const runs = historyRes.runs || historyRes || [];
      setHistory(runs);
      setError(null);
      setConnected(true);
    } catch (err) {
      console.error('Failed to fetch optimizer data:', err);
      setError(err.message);
      setConnected(false);
    } finally {
      setLoading(false);
    }
  }, [siteId]);

  useEffect(() => {
    // Initial fetch
    refresh();

    // Subscribe to real-time updates via SSE
    const unsubscribe = subscribeToOptimizer(
      siteId,
      (update) => {
        setConnected(true);

        // Handle different update types
        if (update.simulation) {
          setStatus(prev => ({ ...prev, ...update.simulation }));
        }
        if (update.run) {
          setHistory(prev => [update.run, ...prev.slice(0, 167)]);
        }
        if (update.telemetry) {
          setStatus(prev => ({
            ...prev,
            currentPvKw: update.telemetry.pvKw ?? prev?.currentPvKw,
            currentDemandKw: update.telemetry.demandKw ?? prev?.currentDemandKw,
            batterySocPct: update.telemetry.socPct ?? prev?.batterySocPct,
            batterySocKwh: update.telemetry.socKwh ?? prev?.batterySocKwh,
            currentPriceAriary: update.telemetry.priceAriary ?? prev?.currentPriceAriary,
            currentChargeKw: update.telemetry.chargeKw ?? prev?.currentChargeKw,
            currentCurtailKw: update.telemetry.curtailKw ?? prev?.currentCurtailKw,
          }));
        }
      },
      (err) => {
        setConnected(false);
        console.error('SSE connection error:', err);
      }
    );

    // Refresh every 30 seconds as fallback
    const interval = setInterval(refresh, 30000);

    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, [siteId, refresh]);

  return { status, history, loading, error, connected, refresh };
}

export default useOptimizerData;
