# KORA Pitch Deck
## Catalyst Fund Application

---

## SLIDE 1: TITLE

# KORA
### The Intelligence Layer for Microgrids

**Transforming wasted solar into revenue and reliable power**

*Catalyst Fund Application | April 2026*

---

## SLIDE 2: THE PROBLEM

# 70% of Solar Energy is Wasted

**The Microgrid Paradox:**

| Morning | Midday | Evening |
|---------|--------|---------|
| Battery charges | Battery FULL | Battery EMPTY |
| Solar ramping up | Solar curtailed | Blackouts begin |
| Customers sleeping | Customers can't afford | Customers desperate |

**Real data from Mahavelona, Madagascar:**
- Daily solar production: **548 kWh**
- Daily energy sold: **165 kWh** (30%)
- Daily curtailment: **383 kWh** (70%)
- Revenue lost: **$85/day = $31,000/year**

**Why?** Fixed pricing can't respond to supply. When batteries are full at 10am, there's nowhere for solar to go—and no incentive for customers to use more.

---

## SLIDE 3: THE SOLUTION

# KORA: Real-Time Optimization + Dynamic Pricing

**We turn curtailment into revenue.**

| When Solar is Abundant | When Supply is Tight |
|------------------------|----------------------|
| KORA lowers prices | KORA raises prices |
| Customers shift demand | Demand reduces |
| Energy gets sold | Battery protected |
| Zero waste | Zero blackouts |

**The Result:**
- Curtailment: **70% → 9%**
- Revenue: **3x increase**
- Customer bills: **18% lower** (they pay less on average)
- Blackouts: **Eliminated**

*Everyone wins: operators, customers, and the planet.*

---

## SLIDE 4: HOW IT WORKS

# The KORA Stack

```
┌─────────────────────────────────────────────┐
│              KORA CLOUD                     │
│  ┌─────────────────────────────────────┐   │
│  │  OPTIMIZER (every 15 minutes)       │   │
│  │  • Demand forecast                  │   │
│  │  • Solar forecast                   │   │
│  │  • Battery state                    │   │
│  │  • Price optimization               │   │
│  └─────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┘
                   │
          Cellular/Satellite
                   │
┌──────────────────▼──────────────────────────┐
│           EDGE AGENT (Raspberry Pi)         │
│  • Modbus connection to inverter/battery    │
│  • Real-time telemetry (5-second intervals) │
│  • Offline buffer (works without internet)  │
│  • Executes dispatch commands               │
└─────────────────────────────────────────────┘
```

**Customer Experience:**
- SMS/WhatsApp: "Low prices today 10am-2pm! Great time for laundry."
- Simple, predictable price tiers they can understand
- Average bill goes DOWN while usage goes UP

---

## SLIDE 5: DEMO RESULTS

# Simulation: Mahavelona Site (Real Data)

### Before KORA (Baseline)
| Metric | Value |
|--------|-------|
| Energy Sold | 165 kWh/day |
| Curtailment | 383 kWh/day (70%) |
| Revenue | $65/day |
| Blackouts | 3 hours/day |

### After KORA (Optimized)
| Metric | Value | Change |
|--------|-------|--------|
| Energy Sold | 498 kWh/day | **+202%** |
| Curtailment | 50 kWh/day (9%) | **-87%** |
| Revenue | $194/day | **+198%** |
| Blackouts | 0 hours/day | **Eliminated** |

**Annual Impact: +$47,000 revenue per site**

*Based on 12,000+ optimization runs with real operational data*

---

## SLIDE 6: MARKET OPPORTUNITY

# $380B Market, Massive Inefficiency

**The Grid is Fragmenting:**
- **1.5 billion people** will get electricity from distributed sources by 2035
- **210 GW** of new capacity needed in Africa alone—70% will be distributed
- **15,000+ rural microgrids** operating today, most with >50% curtailment

**Market Segmentation:**

| Segment | Sites | Our Entry Point |
|---------|-------|-----------------|
| Rural African Microgrids | 15,000 | **NOW** |
| Urban African C&I | 50,000+ | Year 2 |
| Emerging Market Islands | 5,000+ | Year 2-3 |
| Grid-Connected DERs | 500,000+ | Year 3-4 |

**TAM:** $15B+ (distributed energy management software)
**SAM:** $500M (African microgrid optimization)
**SOM:** $50M (initial target operators)

---

## SLIDE 7: BUSINESS MODEL

# SaaS + Performance Fees

### Revenue Streams

| Stream | Price | % of Revenue |
|--------|-------|--------------|
| **SaaS Subscription** | $300-500/site/month | 70% |
| **Performance Fee** | $0.01-0.02/kWh incremental | 20% |
| **Implementation** | $500/site onboarding | 10% |

### Unit Economics (Pro Tier Site)

| Metric | Value |
|--------|-------|
| Monthly Revenue | $522 |
| Monthly Cost | $90 |
| **Gross Margin** | **83%** |
| LTV (24-month) | $10,380 |
| CAC (target) | $1,500 |
| **LTV:CAC** | **6.9x** |

**Payback for Customers:** 15 days (SaaS) or 4 months (license)

---

## SLIDE 8: TRACTION

# From Simulation to Production

### What We've Built
- **Working optimizer** (Gurobi/HiGHS) with proven 70%→9% curtailment reduction
- **Full simulation platform** with 12,000+ test runs
- **Edge agent prototype** (Raspberry Pi + Modbus)
- **Operator dashboard** (mobile-first React app)
- **API layer** (Express.js + PostgreSQL)

### Partnerships Secured

| Partner | Type | Status |
|---------|------|--------|
| **Africa GreenTec** | Anchor Customer | Pilot agreement signed |
| **UCSD DERConnect** | Technical | Partnership active |

### Immediate Pipeline
- **Africa GreenTec:** 25 sites across Madagascar, Mali, Niger
- **PowerGen:** 100+ sites in Kenya, Tanzania (warm intro)
- **Husk Power:** 200+ sites in India, Nigeria (target)

---

## SLIDE 9: COMPETITIVE ADVANTAGE

# Purpose-Built for Microgrids

| Competitor | Their Focus | Why KORA Wins |
|------------|-------------|---------------|
| **SparkMeter** | Hardware + metering | We're software-only, hardware-agnostic |
| **SteamaCo** | East Africa operations | We're optimization-first, not acquired |
| **AutoGrid** | Enterprise VPPs ($100k+) | We're affordable for small grids |
| **In-house** | Custom solutions | We're a platform with ML at scale |

### Our Moat

1. **Data Network Effects** — Every site trains the model, improving forecasts for all
2. **Switching Costs** — Integrated into daily operations, customer success relationship
3. **Geographic Lock-in** — First mover in each region captures partnerships
4. **Technical Complexity** — Optimization + ML + grid physics is hard to replicate

---

## SLIDE 10: CLIMATE IMPACT

# Every kWh Counts

### Direct Impact
- **87% reduction in solar curtailment** = more clean energy utilized
- **Diesel backup reduction** = lower emissions per site
- **Extended battery life** = less e-waste, better economics

### At Scale (500 sites by 2030)
| Metric | Annual Impact |
|--------|---------------|
| Additional clean energy delivered | **75,000 MWh** |
| CO2 emissions avoided | **45,000 tons** |
| Diesel fuel displaced | **8M liters** |
| Additional households powered | **150,000** |

### Climate Resilience
- **Adapts to weather variability** — optimizer responds to clouds, seasons
- **Reduces grid dependency** — communities self-sufficient with renewables
- **Scales clean energy access** — makes microgrids economically viable

---

## SLIDE 11: ROADMAP

# From Pilot to Platform

### 2026: First Production Sites
| Quarter | Milestone | Sites | MRR |
|---------|-----------|-------|-----|
| Q2 | Mahavelona live, first paying customer | 3 | $1,500 |
| Q3 | Pre-seed closed, second country | 7 | $5,000 |
| Q4 | ML forecasting, mobile money | 11 | $15,000 |

### 2027: Product-Market Fit
| Quarter | Milestone | Sites | MRR |
|---------|-----------|-------|-----|
| Q1 | Seed closed ($750k-1.5M) | 14 | $25,000 |
| Q2 | 5 countries, ML GA | 22 | $35,000 |
| Q4 | KORA Grid beta (multi-site) | 50 | $80,000 |

### 2028-2030: Scale
- **Year 3:** 180 sites, Series A, $2.4M ARR
- **Year 4:** 400 sites, energy trading launch, $6M ARR
- **Year 5:** 750 sites, $15M ARR, platform for distributed energy

---

## SLIDE 12: TEAM

# Technical Founder, Building the Team

### Founder
**Brayden Smith** — CEO & Technical Founder
- Deep expertise in optimization, distributed systems, software engineering
- Built the entire KORA stack: optimizer, API, dashboard, edge agent
- Background in [your background]

### Advisors & Partners
- **UCSD DERConnect Team** — Hardware abstraction, academic credibility
- **Africa GreenTec** — On-ground operations, pilot site access

### Key Hires (With This Funding)
| Role | Why Critical | Timeline |
|------|--------------|----------|
| **CTO / Technical Co-founder** | Scale architecture, lead engineering | Q2-Q3 2026 |
| **Head of Customer Success** | Operator relationships, Africa presence | Q3 2026 |

*Actively seeking technical co-founder with distributed systems and/or energy experience*

---

## SLIDE 13: FINANCIALS

# Path to $15M ARR

### 5-Year Projections

| Year | Sites | ARR | Gross Margin | Team | Status |
|------|-------|-----|--------------|------|--------|
| 2026 | 11 | $180k | 80% | 3 | Pre-seed |
| 2027 | 50 | $600k | 82% | 7 | Seed |
| 2028 | 180 | $2.4M | 83% | 15 | Series A |
| 2029 | 400 | $6M | 84% | 30 | Scaling |
| 2030 | 750 | $15M | 85% | 60 | Series B |

### Use of Funds (Pre-Seed: $100-150k)

| Category | Allocation | Purpose |
|----------|------------|---------|
| Engineering | 50% | Complete edge agent, ML forecasting v1 |
| Pilot Expansion | 25% | 3 sites live, hardware, travel |
| Operations | 15% | Cloud infrastructure, tools |
| Legal/Admin | 10% | Incorporation, contracts |

**Runway:** 9-12 months to seed metrics

---

## SLIDE 14: THE ASK

# $100-150k Pre-Seed

### What We'll Achieve
- **3 production sites** running KORA in auto mode
- **$1,500+ MRR** from paying customers
- **Documented case study** with 70%→<15% curtailment proof
- **Seed-ready metrics** for $750k-1.5M raise

### Why Catalyst Fund?
- **Climate focus** — KORA directly increases clean energy utilization
- **Africa focus** — Starting in Madagascar, expanding continent-wide
- **Early stage** — Pre-revenue, but proven technology and signed pilot
- **Capital efficient** — Software-first, low burn, high leverage

### Timeline
| Date | Milestone |
|------|-----------|
| April 2026 | Mahavelona pilot live (advisory mode) |
| May 2026 | Auto mode enabled, measuring results |
| June 2026 | 3 sites, first revenue, case study |
| Q3 2026 | Pre-seed closed, second country |

---

## SLIDE 15: VISION

# The Operating System for Distributed Energy

**Today:** Single-site optimization for rural microgrids

**Year 2:** Multi-site coordination, energy sharing between grids

**Year 3:** P2P energy trading, grid services markets

**Year 5:** The platform that powers the distributed energy transition

---

# 🎯 KORA

**Stop wasting 70% of your solar.**
**Start tripling your revenue.**

*Let's talk: [email] | [phone]*

---

## APPENDIX SLIDES

### A1: Technical Architecture Detail

```
┌─────────────────────────────────────────────────────────────┐
│                   PRODUCTION ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐                    ┌─────────────┐        │
│  │  Edge Agent │───(Cellular/       │   KORA      │        │
│  │  (Rasp Pi)  │   Satellite)──────▶│   Cloud     │        │
│  └──────┬──────┘                    │  (Hetzner)  │        │
│         │                           └──────┬──────┘        │
│    ┌────┴────┐                             │               │
│    │ Modbus  │                      ┌──────┴──────┐        │
│    │ TCP/RTU │                      │  Services   │        │
│    └────┬────┘                      ├─────────────┤        │
│         │                           │ • Express   │        │
│  ┌──────┴──────┐                    │ • Optimizer │        │
│  │  Inverter   │                    │ • Scheduler │        │
│  │  Battery    │                    │ • TimescaleDB│       │
│  │  Meters     │                    └─────────────┘        │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

**Stack:** Python optimizer (Gurobi/HiGHS), Express.js API, React dashboard, PostgreSQL + TimescaleDB, Raspberry Pi edge agents

---

### A2: Customer ROI Calculator

**Site Profile:** 100 kW solar, 200 kWh battery, 50 households

| Metric | Before KORA | After KORA | Delta |
|--------|-------------|------------|-------|
| Monthly Revenue | $1,950 | $5,820 | **+$3,870** |
| Annual Revenue | $23,400 | $69,840 | **+$46,440** |
| KORA Cost (SaaS) | $0 | $500/mo | -$6,000/yr |
| **Net Annual Gain** | — | — | **+$40,440** |

**ROI:** 674% | **Payback:** 15 days

---

### A3: Competitive Landscape Map

```
                    HIGH PRICE
                        │
           AutoGrid     │     Opus One
           (VPPs)       │     (DERMS)
                        │
    ──────────────────────────────────────
    SMALL GRIDS         │         LARGE GRIDS
                        │
           KORA ◄───────│     SteamaCo
           (target)     │     (acquired)
                        │
                    LOW PRICE
```

---

### A4: Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Optimizer fails in production | Failsafe mode, advisory rollout, health checks |
| Connectivity issues | Edge caching, offline mode, async sync |
| Slow customer adoption | Performance guarantees, land-and-expand |
| Competition | Move fast, vertical focus, data moat |
| Key person risk | Seeking co-founder, documenting everything |

---

### A5: Contact

**Brayden Smith**
Founder & CEO, KORA

Email: [your email]
Phone: [your phone]
Website: [kora.energy or similar]
GitHub: [if public]

*Based in [your location]*
*Pilots in Madagascar*

---

*Last updated: April 2026*