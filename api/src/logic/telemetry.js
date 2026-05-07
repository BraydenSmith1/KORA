import { parseThresholds } from './session.js';

const OVERVOLTAGE_THRESHOLD = 252.0;

export function safeJson(value){
  if(value === null || value === undefined) return null;
  if(typeof value === 'object') return value;
  try{
    return JSON.parse(value);
  }catch(_err){
    return null;
  }
}

export function mapTelemetryFrame(row){
  return {
    id: row.id,
    sessionId: row.sessionId,
    tsGateway: row.tsGateway,
    seq: row.seq,
    signals: safeJson(row.signals) || {},
    quality: row.quality || null,
    alerts: safeJson(row.alerts) || [],
    createdAt: row.createdAt
  };
}

export function summarizeFrames(frames, thresholdsRaw){
  if(!frames?.length) return { count: 0, voltage: null, frequency: null, overvoltageCount: 0, overvoltageDurationSec: 0 };
  const thresholds = parseThresholds(thresholdsRaw);
  const ovl = thresholds.ovl_v ?? OVERVOLTAGE_THRESHOLD;

  const sorted = [...frames].sort((a, b)=>new Date(a.tsGateway) - new Date(b.tsGateway));
  let overCount = 0;
  let durationMs = 0;

  const voltageValues = [];
  const freqValues = [];
  for(let i = 0; i < sorted.length; i++){
    const sig = sorted[i].signals || {};
    const v = Number(sig['feeder.voltage_v']);
    const f = Number(sig['feeder.frequency_hz']);
    if(Number.isFinite(v)) voltageValues.push(v);
    if(Number.isFinite(f)) freqValues.push(f);

    if(Number.isFinite(v) && v > ovl){
      overCount += 1;
      const nextTs = sorted[i + 1]?.tsGateway ? new Date(sorted[i + 1].tsGateway).getTime() : new Date(sorted[i].tsGateway).getTime();
      const currTs = new Date(sorted[i].tsGateway).getTime();
      if(nextTs && currTs) durationMs += Math.max(0, nextTs - currTs);
    }
  }

  const avg = (arr) => arr.length ? arr.reduce((s, n)=>s + n, 0) / arr.length : null;
  const max = (arr) => arr.length ? Math.max(...arr) : null;
  const min = (arr) => arr.length ? Math.min(...arr) : null;

  return {
    count: frames.length,
    voltage: { avg: avg(voltageValues), min: min(voltageValues), max: max(voltageValues) },
    frequency: { avg: avg(freqValues), min: min(freqValues), max: max(freqValues) },
    overvoltageCount: overCount,
    overvoltageDurationSec: durationMs / 1000
  };
}

export function integrateTradeEnergy(frames){
  if(!frames?.length) return { matchedKwh: 0 };
  const sorted = [...frames].sort((a, b)=>new Date(a.tsGateway) - new Date(b.tsGateway));
  let matchedKwh = 0;
  for(let i = 0; i < sorted.length - 1; i++){
    const curr = sorted[i];
    const next = sorted[i + 1];
    const power = Number(curr.signals?.['market.trade_power_kw']);
    if(!Number.isFinite(power)) continue;
    const dtHours = (new Date(next.tsGateway).getTime() - new Date(curr.tsGateway).getTime()) / (1000 * 3600);
    matchedKwh += Math.max(0, power) * Math.max(0, dtHours);
  }
  return { matchedKwh };
}
