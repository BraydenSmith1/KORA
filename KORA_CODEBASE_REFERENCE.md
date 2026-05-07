# KORA - Microgrid Intelligence Layer: Complete Codebase Reference

## Overview

**KORA** is an intelligence layer for microgrids that reduces solar curtailment from 70% to <10% through dynamic pricing, battery dispatch, and eventually networked grid coordination. Current pilot site: **Mahavelona, Madagascar** (Africa GreenTec partnership).

- **Version**: 0.3.0 (MVP/Pilot Phase)
- **Status**: Simulation proven, pre-revenue, deploying to first pilot
- **Tech Stack**: Express.js, React, Python/Pyomo, PostgreSQL, Docker

---

## Project Structure

```
/p2p-energy-mvp-full/
├── api/                    # Express.js backend (2,611 lines in server.js)
├── web/                    # React + Vite dashboard (1,463 lines in KoraDemo.jsx)
├── python-optimizer/       # Pyomo MILP optimization engine
├── mobile/                 # React Native app (partial)
├── contracts/              # Solidity smart contracts (Polygon)
├── scripts/                # Deployment/backup scripts
├── monitoring/             # Health monitoring config
├── docs/                   # Documentation
├── docker-compose.yml      # Production orchestration
└── KORA_*.md               # Strategic documents
```

---

## 1. API Layer (Express.js + Prisma + PostgreSQL)

**Location**: `api/`

### Core Files

| File | Purpose |
|------|---------|
| `src/server.js` | Main API (2,611 lines) - all routes, middleware, auth |
| `src/logic/session.js` | Session state management |
| `src/logic/telemetry.js` | Telemetry processing & mapping |
| `src/adapters/payments.js` | Wallet debit/credit operations |
| `src/adapters/chain.js` | Polygon blockchain integration |
| `src/lib/logger.js` | Winston + Axiom logging |
| `prisma/schema.prisma` | Database schema (25 models) |

### Authentication

- **JWT-based** (HS256, 7-day expiry)
- **Password hashing**: PBKDF2-SHA512, 100k iterations, 16-byte salt
- **Legacy fallback**: `x-user-id` header
- **Gateway token**: `x-gateway-token` for edge agents

### Key Routes

#### Auth
- `POST /auth/register` - User registration
- `POST /auth/login` - JWT generation
- `POST /auth/pilot-login` - Pilot user login (operator/anchor roles)
- `POST /auth/forgot-password` / `POST /auth/reset-password`

#### Telemetry
- `GET /api/stream` - SSE real-time telemetry broadcast
- `POST /api/ingest` - Receive Modbus collector data
- `POST /pilot/telemetry` - Gateway-authenticated telemetry
- `GET /pilot/telemetry/latest` - Latest frame
- `GET /pilot/telemetry/frames` - Historical (limit 500)

#### Session
- `GET /session/state` - Active session
- `POST /session/start` - Create session (closes others)
- `POST /session/pause` / `POST /session/stop`

#### Market
- `POST /market/price` - Update price (USD/kWh)
- `POST /market/ev-setpoint` - EV charging setpoint

#### KPIs (`GET /pilot/kpi/:view`)
- `grid-health` - Voltage/frequency
- `control-effectiveness` - Setpoint tracking
- `market-performance` - Trade energy/pricing
- `coupling-intelligence` - Voltage relief per kWh

#### Controls
- `GET /controls/current` - Pending commands
- `POST /controls/:id/ack` - Acknowledge execution

---

## 2. Database Schema (Prisma)

**25 models** across Users, Trading, Telemetry, Forecasting, Simulation:

### Core Models

```prisma
User {
  email, passwordHash, name, phone, organization, timezone, regionId
  → assets[], offers[], requests[], buyerTrades[], sellerTrades[], wallet
}

Wallet { userId (unique), currency, balanceCents, paymentMethod }

Asset { ownerId, label, regionId, capacityKw → meter }

Meter { assetId (unique), whTotal, updatedAt }
```

### P2P Trading

```prisma
Offer { userId, regionId, priceCentsPerKwh, quantityKwh, filledKwh, status }
Request { userId, regionId, maxPriceCentsPerKwh, quantityKwh, filledKwh, reservedCents }
Trade { buyerId, sellerId, offerId, requestId, priceCentsPerKwh, quantityKwh, status }
```

### Session & Telemetry

```prisma
SessionState { sessionId, marketActive, paused, priceUsdPerKwh, thresholds (JSON) }
ControlCommand { sessionId, type, payload (JSON), status }
TelemetryFrame { sessionId, tsGateway, seq, signals (JSON), quality, alerts }
```

### Site Configuration

```prisma
Site {
  name, location, timezone
  pvCapacityKwp: 118.5, batteryCapacityKwh: 115, batteryPowerKw: 100
  socMinPct: 20, socMaxPct: 95
  priceMinAriary, priceMaxAriary, priceRefAriary
  peakDemandKw, baseDemandKw, customerCount: 251
}
```

### Simulation & Optimization

```prisma
OptimizerRun {
  siteId, runId, simulatedTime, solver, solveTimeSec, curtailmentRate
  priceSchedule, batterySchedule, pvForecast, demandForecast
}

SimulationState {
  siteId, isRunning, isPaused, timeAcceleration
  batterySocKwh, batterySocPct, currentPvKw, currentDemandKw, currentPriceAriary
  totalEnergyKwh, totalCurtailKwh, totalRevenueAr
}

SimTelemetry { siteId, simulatedTime, pvKw, demandKw, priceAriary, socKwh, curtailKw }
```

### Forecasting

```prisma
WeatherForecast { siteId, forecastTime, targetTime, ghi, dni, cloudCover, temperature }
PVForecast { siteId, forecastTime, horizonHours, pvKwArray (JSON), method, maeKw }
DemandForecast { siteId, forecastTime, demandKwArray (JSON), method, dayType }
OutageRiskAssessment { siteId, assessmentTime, overallRisk, socRisk, demandRisk, alertLevel }
```

---

## 3. Frontend Dashboard (React + Vite + Recharts)

**Location**: `web/`

### Core Files

| File | Purpose |
|------|---------|
| `src/KoraDemo.jsx` | Main dashboard (1,463 lines) - all tabs |
| `src/api/kora.js` | API client (fetch wrappers) |
| `src/hooks/useOptimizerData.js` | Real-time status + history polling |
| `src/hooks/useForecastData.js` | PV/demand forecast fetching |
| `src/utils/transformData.js` | Data transformation for charts |
| `src/utils/pdfReport.js` | PDF report generation (jsPDF) |

### Dashboard Tabs

1. **Live** - Real-time metrics with gauges
2. **Forecast** - PV/demand 24h prediction
3. **Analysis** - Charts (solar vs load, battery SOC, revenue)
4. **Risk** - Outage probability assessment
5. **Settings** - Site configuration
6. **Help** - User guide

### Site Configuration (Default)

```javascript
siteName: 'Mahavelona'
pvKwp: 118.5, battKwh: 115.2, invKw: 100
connections: 500, peakLoadKw: 52.9
tariffPeak: 1900, tariffMid: 1850, tariffOff: 1700 (Ariary/kWh)
horizonHours: 168 (7 days)
```

### API Client Functions

```javascript
getOptimizerStatus(siteId)      // GET /api/optimizer/status
getOptimizerHistory(siteId)     // GET /api/optimizer/history
subscribeToOptimizer(siteId)    // EventSource /api/optimizer/stream
getPVForecast(siteId, hours)    // GET /api/forecast/pv
getDemandForecast(siteId)       // GET /api/forecast/demand
getRiskAssessment(siteId)       // GET /api/forecast/risk
startSimulation(siteId)         // POST /api/simulation/start
pauseSimulation(siteId)         // POST /api/simulation/pause
resetSimulation(siteId)         // POST /api/simulation/reset
```

### Tech Stack

- React 18, Vite, TailwindCSS
- Recharts (charts), Lucide React (icons)
- ethers.js (blockchain), jsPDF (reports)

---

## 4. Python Optimizer (Pyomo + Gurobi/HiGHS)

**Location**: `python-optimizer/`

### Core Architecture

```
python-optimizer/
├── kora/                      # Main package
│   ├── config.py              # YAML-based site config
│   ├── service.py             # OptimizerRunner (production)
│   ├── simulation.py          # SimulationRunner (demo)
│   ├── cache.py               # Result caching
│   ├── errors.py              # Exception hierarchy + retry
│   ├── telemetry.py           # Modbus integration
│   └── forecasting/           # Forecasting subpackage
│       ├── solar.py           # PV generation
│       ├── demand.py          # Load forecasting
│       ├── weather.py         # Open-Meteo API
│       ├── risk.py            # Outage assessment
│       └── service.py         # Orchestration
├── optimizer/
│   ├── model.py               # Simple Pyomo MILP (185 lines)
│   └── gurobi_model.py        # Advanced Gurobi model (32KB)
├── run_optimizer.py           # Standalone demo
├── modbus_collector.py        # Modbus TCP → API
└── mahavelona_config.py       # Site specs
```

### Optimization Model (Pyomo MILP)

**Inputs**:
- `load_kw`, `pv_kw`: hourly profiles (24-168 hours)
- `price_buy`, `price_sell`: tariffs
- Battery: capacity, power, SOC bounds, efficiency, cycle cost
- Penalties: curtailment, load shedding

**Decision Variables**:
- `p_charge[t]`, `p_discharge[t]` (kW)
- `soc[t]` (kWh)
- `p_grid_import[t]`, `p_grid_export[t]`
- `p_curtail[t]`, `p_shed[t]`
- `y_charge[t]`, `y_discharge[t]` (binary exclusivity)

**Objective**: Minimize
```
purchase_cost - export_revenue + curtailment_penalty + shed_penalty + degradation
```

**Constraints**:
- SOC dynamics: `soc[t] = soc[t-1] + dt*(η_c*p_c - p_d/η_d)`
- Power balance: `pv + import + discharge = load + charge + export + curtail + shed`
- Charge/discharge exclusivity (big-M)
- Grid limits, SOC bounds

### Mahavelona Site Specs

```
PV: 118.5 kWp (300× TrinaSolar 395W)
Battery: 115 kWh TESVOLT (24× 4.8 kWh modules)
Inverter: 100 kW (2× 50 kW SMA)
Daily production: ~548 kWh
Peak load: 53 kW
Customers: 251 (201 households, 34 SMEs, 16 public)
Baseline curtailment: 70% (battery full by 10am)
SOC bounds: 20-95%

Pricing (Ariary/kWh):
  Peak (5-11pm): 1850-1950
  Mid (8am-5pm): 1700-1800
  Off-peak: 1700-1950
```

### Solver Support

- **Gurobi** (preferred, commercial license)
- **HiGHS** (free, MILP capable)
- GLPK, CBC (fallback)

---

## 5. Deployment (Docker)

### docker-compose.yml Services

| Service | Image | Purpose |
|---------|-------|---------|
| `db` | postgres:16-alpine | PostgreSQL database |
| `api` | node:20-alpine | Express API (port 4000) |
| `optimizer` | python-optimizer | KORA optimizer service |
| `web` | nginx:alpine | React dashboard (port 3000) |
| `caddy` | caddy:2-alpine | HTTPS reverse proxy (optional) |

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@db:5432/kora

# API
JWT_SECRET, NODE_ENV, PORT=4000

# Optimizer
KORA_SITE_CONFIG=mahavelona.yaml
KORA_API_URL=http://api:4000
KORA_LOG_LEVEL=INFO
KORA_CACHE_ENABLED=true

# Monitoring
AXIOM_TOKEN, AXIOM_DATASET
SLACK_WEBHOOK_URL

# Blockchain (optional)
CHAIN_RPC_URL, CHAIN_PRIVATE_KEY, CHAIN_CONTRACT_ADDRESS
```

---

## 6. Data Flows

### Real-time Telemetry

```
Modbus RTDS → modbus_collector.py → POST /api/ingest → EventLog
  → broadcastTelemetry() → SSE /api/stream → React dashboard
```

### Optimization Cycle

```
SimulationRunner tick (1s real = 60s simulated)
  → Generate PV/demand forecast
  → OptimizerRunner.run() (Pyomo + solver)
  → Store OptimizerRun + SimTelemetry
  → Update SimulationState (battery SOC)
  → POST /api/telemetry → broadcast
```

### Trading Flow

```
Create Offer/Request → runRegionMatch() → Create Trade
  → PaymentsAdapter (debit buyer, credit seller)
  → ChainAdapter.recordTrade() (blockchain optional)
  → EventLog
```

---

## 7. Key Metrics (Proven)

| Metric | Baseline | Optimized |
|--------|----------|-----------|
| Curtailment | 70% | 9% |
| Revenue potential | 1x | 2-3x |
| Battery utilization | Poor | Full SOC cycling |

---

## 8. Current Status (May 2026)

### Completed

- Simulation system built and validated
- Optimizer works with Gurobi/HiGHS
- 70% → 9% curtailment proven
- Partnerships: Africa GreenTec (pilot), UCSD DERConnect (technical)

### Immediate Priorities

1. DERConnect telemetry integration
2. Edge agent on Raspberry Pi
3. Mahavelona pilot live (advisory → autonomous)
4. Target: $1,500 MRR by end of Q2

### Architecture Gaps

- `/api/stream` SSE endpoint lacks auth
- Simulation not persisted to wallet/trades (demo-only)
- Mobile app partially developed

---

## 9. Long-Term Vision (5 Layers)

1. **Data Infrastructure** - Telemetry, edge computing ✓
2. **Core Optimization** - Dispatch, pricing, battery ✓
3. **Intelligence** - ML forecasting, anomaly detection (next)
4. **Network Coordination** - Multi-site optimization (Year 2)
5. **Markets & Trading** - P2P trading, grid services (Year 3-5)

---

## 10. File Reference Quick Links

### API (Most Important)
- `api/src/server.js` - All routes and business logic
- `api/prisma/schema.prisma` - Database schema
- `api/src/logic/telemetry.js` - Telemetry processing
- `api/src/adapters/payments.js` - Wallet operations

### Frontend
- `web/src/KoraDemo.jsx` - Main dashboard component
- `web/src/api/kora.js` - API client
- `web/src/hooks/useOptimizerData.js` - Data fetching

### Optimizer
- `python-optimizer/optimizer/model.py` - Core MILP model
- `python-optimizer/kora/service.py` - Production runner
- `python-optimizer/kora/simulation.py` - Simulation loop
- `python-optimizer/kora/forecasting/` - All forecasting modules

### Deployment
- `docker-compose.yml` - Production orchestration
- `.env.example` - Environment template
- `api/Dockerfile`, `web/Dockerfile` - Container builds

---

*This document provides complete context for the KORA microgrid intelligence system. The codebase is production-grade with clear separation between API/optimizer/web components, modular architecture for independent scaling, and a proven path from simulation to pilot deployment.*