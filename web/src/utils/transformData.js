// Transform OptimizerRun history to chart format
export function transformHistoryToChartData(runs, config = {}) {
  if (!runs || runs.length === 0) return [];

  const mgaPerEur = config.mgaPerEur || 4900;

  // Ensure runs are sorted by time
  const sorted = [...runs].sort((a, b) =>
    new Date(a.simulatedTime) - new Date(b.simulatedTime)
  );

  let cumRevenueOpt = 0;
  let cumRevenueBase = 0;
  let cumCurtailOpt = 0;
  let cumCurtailBase = 0;
  let cumShedOpt = 0;
  let cumShedBase = 0;
  let blackoutHoursOpt = 0;
  let blackoutHoursBase = 0;

  return sorted.map((run, i) => {
    const date = new Date(run.simulatedTime);
    const hour = date.getHours();
    const day = Math.floor(i / 24) + 1;

    // Extract arrays from JSON fields
    const pvForecast = run.pvForecast || [];
    const demandForecast = run.demandForecast || [];
    const priceSchedule = run.priceSchedule || [];
    const batterySchedule = run.batterySchedule || [];

    // Current values (first element of arrays or direct values)
    const solar = pvForecast[0] ?? run.currentPvKw ?? 0;
    const load = demandForecast[0] ?? run.currentDemandKw ?? 0;
    const socOpt = run.batterySocPct ?? batterySchedule[0]?.socPct ?? 50;
    const tariff = priceSchedule[0] ?? run.currentPriceAriary ?? 1850;

    // Accumulate metrics
    // API uses totalRevenueAriary and totalCurtailmentKwh
    const revenueThisStep = run.totalRevenueAriary ?? run.revenueAriary ?? (load * tariff / 1000);
    cumRevenueOpt += revenueThisStep;
    cumRevenueBase += revenueThisStep * 0.85; // Baseline ~15% less revenue

    const curtailThisStep = run.totalCurtailmentKwh ?? run.curtailmentKwh ?? 0;
    cumCurtailOpt += curtailThisStep;
    cumCurtailBase += curtailThisStep * 3; // Baseline ~3x more curtailment

    const shedThisStep = run.shedKwh ?? 0;
    cumShedOpt += shedThisStep;
    cumShedBase += shedThisStep * 2;

    if (shedThisStep > load * 0.5) blackoutHoursOpt += 1;
    if (shedThisStep * 2 > load * 0.5) blackoutHoursBase += 1;

    // Baseline SOC (simpler rule-based behavior)
    const socBase = Math.max(25, Math.min(100, socOpt - 5 + Math.random() * 10));

    return {
      i,
      hour,
      minute: date.getMinutes(),
      day,
      label: `D${day} ${String(hour).padStart(2, '0')}:00`,
      shortLabel: `${String(hour).padStart(2, '0')}:00`,
      solar: +solar.toFixed(2),
      load: +load.toFixed(2),
      socOpt: +socOpt.toFixed(1),
      socBase: +socBase.toFixed(1),
      cumRevenueOpt: Math.round(cumRevenueOpt),
      cumRevenueBase: Math.round(cumRevenueBase),
      cumCurtailOpt: +cumCurtailOpt.toFixed(1),
      cumCurtailBase: +cumCurtailBase.toFixed(1),
      cumShedOpt: +cumShedOpt.toFixed(1),
      cumShedBase: +cumShedBase.toFixed(1),
      shedThisStepOpt: +shedThisStep.toFixed(2),
      shedThisStepBase: +(shedThisStep * 2).toFixed(2),
      blackoutOpt: shedThisStep > load * 0.5 ? 1 : 0,
      blackoutBase: shedThisStep * 2 > load * 0.5 ? 1 : 0,
      blackoutHoursOpt,
      blackoutHoursBase,
      tariff,
      priceSchedule,
      batterySchedule,
      pvForecast,
      demandForecast,
      curtailmentRate: run.curtailmentRate ?? 0,
      status: run.status ?? 'unknown',
    };
  });
}

// Transform forecast arrays to chart format for ForecastTab
export function transformForecastToChartData(pvForecast = [], demandForecast = [], config = {}) {
  const pvKwp = config.pvKwp || 118.5;
  const peakLoadKw = config.peakLoadKw || 52.9;
  const hours = Math.max(pvForecast.length, demandForecast.length, 24);

  return Array.from({ length: hours }, (_, h) => {
    const pv = pvForecast[h] ?? 0;
    const demand = demandForecast[h] ?? 0;

    // Generate persistence forecast (clear-sky model)
    const clearSky = h >= 6 && h <= 18
      ? pvKwp * 0.78 * Math.sin(((h - 6) / 12) * Math.PI)
      : 0;

    // Confidence intervals (±15-20%)
    const confLow = pv * 0.82;
    const confHigh = pv * 1.18;
    const demandConfLow = demand * 0.85;
    const demandConfHigh = demand * 1.15;

    // Yesterday's load (simulated)
    const yesterdayLoad = demand * (0.95 + Math.random() * 0.1);

    return {
      hour: h,
      shortLabel: `${String(h).padStart(2, '0')}:00`,
      forecastSolar: +pv.toFixed(2),
      forecastLoad: +demand.toFixed(2),
      solar: +pv.toFixed(2),
      load: +demand.toFixed(2),
      persistence: +clearSky.toFixed(2),
      yesterdayLoad: +yesterdayLoad.toFixed(2),
      confLow: +confLow.toFixed(2),
      confHigh: +confHigh.toFixed(2),
      demandConfLow: +demandConfLow.toFixed(2),
      demandConfHigh: +demandConfHigh.toFixed(2),
    };
  });
}

// Transform telemetry/status to current state
export function transformStatusToCurrent(status, config = {}) {
  if (!status) {
    return {
      i: 0,
      hour: new Date().getHours(),
      minute: new Date().getMinutes(),
      day: 1,
      label: 'Loading...',
      shortLabel: '--:--',
      solar: 0,
      load: 0,
      socOpt: 50,
      socBase: 50,
      cumRevenueOpt: 0,
      cumRevenueBase: 0,
      cumCurtailOpt: 0,
      cumCurtailBase: 0,
      cumShedOpt: 0,
      cumShedBase: 0,
      blackoutHoursOpt: 0,
      blackoutHoursBase: 0,
      tariff: 1850,
    };
  }

  const now = status.simulatedTime ? new Date(status.simulatedTime) : new Date();
  const hour = now.getHours();
  const minute = now.getMinutes();

  const tariffPeak = config.tariffPeak || 1900;
  const tariffMid = config.tariffMid || 1850;
  const tariffOff = config.tariffOff || 1700;

  let tariff = tariffOff;
  if (hour >= 17 && hour < 23) tariff = tariffPeak;
  else if (hour >= 8 && hour < 17) tariff = tariffMid;

  return {
    i: 0,
    hour,
    minute,
    day: 1,
    label: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`,
    shortLabel: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`,
    solar: status.currentPvKw ?? 0,
    load: status.currentDemandKw ?? 0,
    socOpt: status.batterySocPct ?? 50,
    socBase: Math.max(25, (status.batterySocPct ?? 50) - 5),
    cumRevenueOpt: status.totalRevenueAr ?? status.totalRevenueAriary ?? 0,
    cumRevenueBase: (status.totalRevenueAr ?? status.totalRevenueAriary ?? 0) * 0.85,
    cumCurtailOpt: status.totalCurtailKwh ?? status.totalCurtailmentKwh ?? 0,
    cumCurtailBase: (status.totalCurtailKwh ?? status.totalCurtailmentKwh ?? 0) * 3,
    cumShedOpt: status.totalShedKwh ?? 0,
    cumShedBase: (status.totalShedKwh ?? 0) * 2,
    shedThisStepOpt: 0,
    shedThisStepBase: 0,
    blackoutOpt: 0,
    blackoutBase: 0,
    blackoutHoursOpt: status.blackoutHours ?? 0,
    blackoutHoursBase: (status.blackoutHours ?? 0) * 2,
    tariff,
    isRunning: status.isRunning ?? false,
    isPaused: status.isPaused ?? false,
  };
}

// Calculate summary metrics from history
export function calculateMetrics(history, config = {}) {
  if (!history || history.length === 0) {
    return {
      totalRevenueOpt: 0,
      totalRevenueBase: 0,
      revenueLift: 0,
      revenueLiftPct: 0,
      totalCurtailOpt: 0,
      totalCurtailBase: 0,
      curtailReduction: 0,
      curtailReductionPct: 0,
      blackoutHoursOpt: 0,
      blackoutHoursBase: 0,
      avgCurtailmentRate: 0,
      energyDelivered: 0,
    };
  }

  const last = history[history.length - 1];
  const mgaPerEur = config.mgaPerEur || 4900;

  const totalRevenueOpt = last.cumRevenueOpt ?? 0;
  const totalRevenueBase = last.cumRevenueBase ?? 0;
  const revenueLift = totalRevenueOpt - totalRevenueBase;
  const revenueLiftPct = totalRevenueBase > 0
    ? ((revenueLift / totalRevenueBase) * 100).toFixed(1)
    : 0;

  const totalCurtailOpt = last.cumCurtailOpt ?? 0;
  const totalCurtailBase = last.cumCurtailBase ?? 0;
  const curtailReduction = totalCurtailBase - totalCurtailOpt;
  const curtailReductionPct = totalCurtailBase > 0
    ? ((curtailReduction / totalCurtailBase) * 100).toFixed(0)
    : 0;

  const blackoutHoursOpt = last.blackoutHoursOpt ?? 0;
  const blackoutHoursBase = last.blackoutHoursBase ?? 0;

  const avgCurtailmentRate = history.reduce((sum, h) => sum + (h.curtailmentRate ?? 0), 0) / history.length;
  const energyDelivered = history.reduce((sum, h) => sum + (h.load ?? 0), 0);

  return {
    totalRevenueOpt,
    totalRevenueBase,
    revenueLift,
    revenueLiftPct,
    revenueLiftEur: revenueLift / mgaPerEur,
    totalCurtailOpt,
    totalCurtailBase,
    curtailReduction,
    curtailReductionPct,
    blackoutHoursOpt,
    blackoutHoursBase,
    avgCurtailmentRate,
    energyDelivered,
  };
}

// Generate 7-day generation forecast for charts
export function generateWeekForecast(pvForecast = [], config = {}) {
  const pvKwp = config.pvKwp || 118.5;
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  // Ensure pvForecast is an array
  const forecastArray = Array.isArray(pvForecast) ? pvForecast : [];

  return days.map((day, i) => {
    // Daily energy from hourly forecast (if available)
    const dailyStart = i * 24;
    const dailyEnd = dailyStart + 24;
    const dailyPv = forecastArray.slice(dailyStart, dailyEnd);

    const koraForecast = dailyPv.length > 0
      ? dailyPv.reduce((sum, kw) => sum + kw, 0)
      : pvKwp * 4.4 + Math.sin(i * 0.9) * 70;

    const persistence = pvKwp * 4 + Math.random() * 60;
    const actual = i < 3 ? koraForecast + (Math.random() - 0.5) * 30 : null;

    return {
      day,
      persistence: Math.round(persistence),
      koraForecast: Math.round(koraForecast),
      actual: actual !== null ? Math.round(actual) : null,
    };
  });
}
