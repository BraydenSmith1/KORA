# KORA: Master Strategy Document
## The Ultimate Intelligence Layer for Microgrids

> **Mission**: Become the dominant software intelligence platform for distributed energy resources, starting with rural African microgrids and scaling to a global networked energy operating system.

**Created**: April 2026
**Last Updated**: April 12, 2026
**Author**: Brayden Smith

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Market Thesis](#market-thesis)
3. [Product Vision & Evolution](#product-vision--evolution)
4. [Refined Business Model](#refined-business-model)
5. [Go-to-Market Strategy](#go-to-market-strategy)
6. [Technical Architecture Roadmap](#technical-architecture-roadmap)
7. [Next Steps: Week, Month, Year, 5 Years](#next-steps)
8. [Execution Checklist](#execution-checklist)
9. [Risks & Mitigations](#risks--mitigations)
10. [Financial Projections](#financial-projections)

---

## Executive Summary

KORA solves the fundamental inefficiency plaguing off-grid and distributed energy: **70% of solar generation is wasted** because batteries fill by 10am while customers sit idle, unable to afford electricity at fixed prices. By deploying real-time optimization with dynamic pricing, KORA converts curtailed energy into revenue—tripling operator economics while reducing customer costs.

**Current State (April 2026)**:
- Working optimizer (Gurobi/HiGHS) with proven 70%→9% curtailment reduction
- Simulation platform fully built
- Pilot partnership with Africa GreenTec (Mahavelona, Madagascar)
- Technical partnership with UCSD DERConnect
- $0 revenue, pre-product-market-fit

**12-Month Target (April 2027)**:
- 14 sites live across 4 countries
- $42,000 MRR (~$500k ARR)
- <10% average curtailment across portfolio
- Seed round closed ($750k-$1.5M)

**5-Year Vision (2031)**:
- 500+ sites under management
- $15M+ ARR
- Networked microgrid coordination across regions
- Energy trading platform connecting distributed generation
- Dominant position in African/emerging market grid intelligence

---

## Market Thesis

### The Opportunity

**The Grid is Fragmenting**. The 20th-century model of centralized generation → transmission → distribution is being replaced by a networked mesh of distributed energy resources (DERs). By 2035:

- **1.5 billion people** will get electricity primarily from distributed sources
- **$380 billion** will be invested in mini-grids and off-grid solar
- **Africa alone** will need 210 GW of new capacity—70% will be distributed

**The Intelligence Gap**. Hardware (solar panels, batteries, inverters) has commoditized. What's missing is the **brain**:
- Real-time optimization across generation, storage, and demand
- Forecasting that adapts to local conditions
- Coordination between assets
- Market participation and value stacking

**KORA's Wedge**: Start where the pain is most acute (rural African microgrids with 70% curtailment) and build the platform that grows with the market.

### Market Segmentation

| Segment | Size | Pain Point | KORA Solution |
|---------|------|------------|---------------|
| **Rural African Microgrids** | 15,000 sites | Massive curtailment, unreliable supply | Core optimizer + dynamic pricing |
| **Urban African C&I** | 50,000+ sites | Grid instability, diesel backup costs | Peak shaving + backup optimization |
| **Emerging Market Islands** | 5,000+ sites | High LCOE, grid isolation | Multi-site coordination |
| **Grid-Connected DERs** | 500,000+ sites | Curtailment, market access | Trading + aggregation |
| **Developed Market VPPs** | 1M+ sites | Value stacking complexity | Full DER management |

### Competitive Landscape

| Competitor | Strength | Weakness | KORA Advantage |
|------------|----------|----------|----------------|
| **SparkMeter** | Hardware + metering | Limited optimization, hardware-centric | Software-only, hardware-agnostic |
| **SteamaCo (Husk)** | East Africa presence | Acquired, less focused | Independent, optimization-first |
| **AutoGrid** | Enterprise VPP | Too expensive for small grids | Purpose-built for microgrids |
| **Opus One** | Utility-scale DERMS | Wrong market segment | Ground-up for distributed |
| **In-house** | Customized | No scale, no ML | Platform approach |

**Moat Strategy**:
1. **Data Network Effects**: Every site trains the model, improving forecasts for all
2. **Switching Costs**: Integrated into operations, customer success relationship
3. **Geographic Lock-in**: First mover in each region captures partnerships
4. **Technical Complexity**: Optimization + ML + grid physics is hard to replicate

---

## Product Vision & Evolution

### The KORA Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    KORA INTELLIGENCE PLATFORM                    │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 5: MARKET & TRADING                                       │
│  • Energy trading between microgrids                             │
│  • Grid services market participation                            │
│  • Carbon credit automation                                      │
│  • P2P energy marketplace                                        │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: NETWORK COORDINATION                                   │
│  • Multi-site portfolio optimization                             │
│  • Cross-microgrid energy sharing                                │
│  • Regional demand aggregation                                   │
│  • Resilience clustering                                         │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: INTELLIGENCE & FORECASTING                             │
│  • ML demand forecasting (site-specific)                         │
│  • Solar irradiance prediction                                   │
│  • Anomaly detection                                             │
│  • Predictive maintenance                                        │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: CORE OPTIMIZATION                    ◄── YOU ARE HERE │
│  • Real-time dispatch optimization                               │
│  • Dynamic pricing engine                                        │
│  • Battery cycle optimization                                    │
│  • Load prioritization                                           │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: DATA INFRASTRUCTURE                                    │
│  • Telemetry ingestion (Modbus, DERConnect)                      │
│  • Edge computing (Raspberry Pi agents)                          │
│  • Time-series database (TimescaleDB)                            │
│  • API layer (REST, GraphQL)                                     │
├─────────────────────────────────────────────────────────────────┤
│  HARDWARE ABSTRACTION                                            │
│  • SMA, Victron, Schneider, Huawei inverters                     │
│  • BYD, Pylontech, SimpliPhi batteries                           │
│  • Smart meters (SparkMeter, Angaza)                             │
└─────────────────────────────────────────────────────────────────┘
```

### Product Evolution Phases

#### Phase 1: KORA Core (Now - Month 12)
**Focus**: Prove the optimizer works in production, get to $500k ARR

- Real-time optimization (15-minute intervals)
- Dynamic pricing with demand response
- Basic forecasting (persistence + weather)
- Operator dashboard (mobile-first)
- Advisory → Auto mode progression
- Basic alerting (SMS, WhatsApp)

**Key Metrics**:
- Curtailment reduction: 70% → <15%
- Revenue increase: 2-3x for operators
- Uptime: >99%

#### Phase 2: KORA Intelligence (Month 9 - Month 24)
**Focus**: Add ML forecasting, prove at scale

- Site-specific demand models (transformer-based)
- Solar nowcasting with satellite data
- Predictive maintenance (battery health, inverter faults)
- Portfolio analytics dashboard
- API for third-party integration
- Multi-tenant white-label option

**Key Metrics**:
- Forecast accuracy: <10% MAPE
- Time to onboard: <48 hours
- Sites per support FTE: 25+

#### Phase 3: KORA Grid (Month 18 - Month 36)
**Focus**: Network effects, multi-site coordination

- Cross-site optimization (regional dispatch)
- Energy sharing between proximate microgrids
- Aggregated demand response programs
- Grid-connected mode (import/export optimization)
- Virtual Power Plant capabilities
- Resilience scoring and recommendations

**Key Metrics**:
- Portfolio-level curtailment: <5%
- Inter-site energy flows: measurable
- Grid services revenue: >10% of total

#### Phase 4: KORA Markets (Month 30 - Month 60)
**Focus**: Energy trading, market participation

- P2P energy trading platform
- Wholesale market integration (where available)
- Ancillary services (frequency response, reserves)
- Carbon credit marketplace
- Green certificate tracking
- Financial settlement layer

**Key Metrics**:
- Trading volume: $10M+ annually
- Take rate: 1-3% of traded value
- New revenue streams: 3+

#### Phase 5: KORA OS (Month 48+)
**Focus**: Become the operating system for distributed energy

- Full DERMS capabilities
- Cybersecurity SOC
- Standards compliance (IEEE 2030.5, OpenADR, IEC 61850)
- Interoperability hub
- Developer ecosystem (apps on KORA)
- Global scale (100+ countries)

---

## Refined Business Model

### Revenue Streams

#### Stream 1: SaaS Subscription (70% of revenue)

| Tier | Price | Includes |
|------|-------|----------|
| **KORA Core** | $300/site/month | Real-time optimization, dynamic pricing, basic dashboard, email support |
| **KORA Pro** | $500/site/month | + ML forecasting, API access, priority support, multi-site view |
| **KORA Enterprise** | $1,500/site/month | + Custom models, white-label, dedicated CSM, SLA |

**Volume Discounts**:
- 5+ sites: 10% off
- 10+ sites: 20% off
- 25+ sites: Custom pricing

#### Stream 2: Performance Fee (20% of revenue)

- **$0.01-0.02/kWh** of additional energy sold (vs baseline)
- Aligns incentives: KORA only makes money when operator makes money
- Measured via A/B testing or historical baseline
- Caps at 2x subscription to prevent runaway costs

#### Stream 3: Implementation & Services (10% of revenue)

| Service | Price |
|---------|-------|
| Site onboarding | $500/site (waived for Enterprise) |
| Custom integration | $150/hour |
| Training (virtual) | $200/session |
| Training (on-site) | $500/day + travel |
| Custom model development | Project-based |

#### Stream 4: Future Revenue (2028+)

- **Energy trading commission**: 1-3% of traded value
- **Carbon credit fees**: $0.50/ton facilitated
- **Data licensing**: Aggregated grid analytics
- **Hardware partnerships**: Referral fees from inverter/battery vendors

### Unit Economics

```
Average Site (Pro tier, 15,000 kWh/month throughput)
──────────────────────────────────────────────────────────────

REVENUE
  Subscription:                    $500/month
  Performance fee (1,500 kWh add'l @ $0.015): $22.50/month
──────────────────────────────────────────────────────────────
  Total Revenue:                   $522.50/month

COSTS
  Cloud infrastructure:            $15/month
  Support (allocated):             $35/month
  Customer success (allocated):    $25/month
  Payment processing (3%):         $15/month
──────────────────────────────────────────────────────────────
  Total Cost:                      $90/month

MARGINS
  Gross Margin:                    83%
  LTV (24-month avg tenure):       $10,380
  CAC (target):                    $1,500
  LTV:CAC:                         6.9x
```

### Pricing Philosophy

1. **Value-based, not cost-based**: Price at 10-20% of value created
2. **Land and expand**: Start with 1-2 sites, prove value, expand
3. **Annual contracts preferred**: 15% discount for annual prepay
4. **No free tier**: Free pilot for 30 days, then paid (even $100/month validates)

---

## Go-to-Market Strategy

### Phase 1: Lighthouse Accounts (Now - Month 6)

**Goal**: 3-5 reference customers with documented results

**Target Profile**:
- African mini-grid developers with 5+ sites
- Significant curtailment (>40%)
- Technical team can support integration
- Willingness to be a reference

**Priority Targets** (in order):

1. **Africa GreenTec** (existing relationship)
   - Status: Pilot partnership in place
   - Sites: 25 across Madagascar, Mali, Niger
   - Next step: Close Mahavelona pilot, expand to 5 sites

2. **PowerGen Renewable Energy**
   - Sites: 100+ across Kenya, Tanzania, Nigeria
   - Approach: Warm intro via DERConnect
   - Value prop: Portfolio-wide optimization

3. **Husk Power Systems**
   - Sites: 200+ across India, Nigeria
   - Approach: Conference meeting, cold outreach
   - Value prop: Reduce curtailment at scale

4. **BBOXX**
   - Sites: 200,000+ SHS, expanding to mini-grids
   - Approach: Partnership discussion
   - Value prop: White-label optimization for mini-grid product

5. **CrossBoundary Energy Access**
   - Structure: Asset owner/financier
   - Approach: Portfolio optimization pitch
   - Value prop: Improve returns across portfolio

**Sales Motion**:
1. Demo (show their curtailment data if available)
2. 30-day free pilot on 1-2 sites
3. Results review meeting
4. Proposal for full deployment
5. Quarterly business reviews

### Phase 2: Channel Partnerships (Month 6 - Month 18)

**Goal**: Leverage partners for distribution

| Partner Type | Examples | Model |
|--------------|----------|-------|
| **Hardware distributors** | Victron Energy, SMA | Bundled offering, referral fees |
| **Project developers** | Engie, EDF | White-label, per-site fee |
| **Financiers** | SunFunder, Norfund | Required for portfolio companies |
| **Industry associations** | AMDA, ARE | Preferred vendor, conference presence |

### Phase 3: Inbound Marketing (Month 6 - Month 24)

**Content Strategy**:
- Monthly blog posts (technical + business)
- Quarterly whitepapers (ROI studies, technical guides)
- Annual industry report (State of Microgrid Optimization)

**Conference Presence**:
- AMDA Summit (Africa Mini-grid Developers Association)
- ARE Energy Access Forum
- GOGLA Off-Grid Solar Forum
- Intersolar (as market expands)

**Digital Presence**:
- SEO: "microgrid optimization", "curtailment reduction"
- LinkedIn: Thought leadership, customer stories
- Newsletter: Weekly energy access insights

### Geographic Expansion Sequence

```
2026-2027: AFRICA FOUNDATION
├── Madagascar (Q1-Q2): Africa GreenTec anchor
├── Kenya (Q2-Q3): PowerGen, mobile money integration
├── Rwanda (Q3-Q4): BBOXX, government relationship
└── Nigeria (Q4): Husk Power, largest market

2027-2028: AFRICAN SCALE
├── Tanzania: PowerGen expansion
├── Uganda: MTN partnership
├── Ghana: Emerging player
└── Senegal: French-speaking expansion

2028-2029: EMERGING MARKETS
├── India: Husk Power, OMC Power
├── Philippines: Island grids
├── Indonesia: Off-grid islands
└── Caribbean: Island utilities

2029-2031: DEVELOPED MARKETS
├── Australia: Grid-edge DERs
├── US (Hawaii, Puerto Rico): Island grids
├── Europe: Community energy
└── Global scale
```

---

## Technical Architecture Roadmap

### Current State (April 2026)

```
┌─────────────────────────────────────────────────────────────┐
│                     CURRENT ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  React SPA  │────│ Express API │────│ PostgreSQL  │     │
│  │  (Vite)     │    │ (Node.js)   │    │ (Prisma)    │     │
│  └─────────────┘    └──────┬──────┘    └─────────────┘     │
│                            │                                │
│                     ┌──────┴──────┐                        │
│                     │   Python    │                        │
│                     │  Optimizer  │                        │
│                     │  (Gurobi/   │                        │
│                     │   HiGHS)    │                        │
│                     └─────────────┘                        │
│                                                             │
│  Status: Simulation-only, no real telemetry                │
└─────────────────────────────────────────────────────────────┘
```

### Phase 1 Architecture (Month 1-6)

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
│         │                           │ • API       │        │
│  ┌──────┴──────┐                    │ • Optimizer │        │
│  │  Inverter   │                    │ • Scheduler │        │
│  │  Battery    │                    │ • Alerts    │        │
│  │  Meters     │                    └─────────────┘        │
│  └─────────────┘                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Components**:

1. **Edge Agent** (Python, runs on Raspberry Pi)
   - Collects telemetry via Modbus every 5 seconds
   - Local SQLite buffer for offline operation
   - Executes dispatch commands from cloud
   - Failsafe mode if cloud connection lost

2. **KORA Cloud** (Hetzner, Docker Compose → Kubernetes later)
   - **API Service**: Express.js, REST + SSE
   - **Optimizer Service**: Python, Gurobi Cloud
   - **Scheduler**: Cron-based optimization runs
   - **Database**: PostgreSQL + TimescaleDB extension
   - **Cache**: Redis for real-time data

3. **DERConnect Integration**
   - Standardized telemetry format
   - Automatic device discovery
   - Configuration management

### Phase 2 Architecture (Month 6-18)

```
┌─────────────────────────────────────────────────────────────┐
│                   SCALED ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────┐       │
│  │                 KUBERNETES CLUSTER               │       │
│  │                                                  │       │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐          │       │
│  │  │   API   │ │Optimizer│ │   ML    │          │       │
│  │  │ (x3)   │ │  (x5)   │ │ Workers │          │       │
│  │  └────┬────┘ └────┬────┘ └────┬────┘          │       │
│  │       │           │           │                │       │
│  │       └───────────┴───────────┘                │       │
│  │                   │                            │       │
│  │       ┌───────────┴───────────┐                │       │
│  │       │                       │                │       │
│  │  ┌────┴────┐           ┌──────┴──────┐        │       │
│  │  │Timescale│           │    Redis    │        │       │
│  │  │   DB    │           │   Cluster   │        │       │
│  │  └───��─────┘           └─────────────┘        │       │
│  └─────────────────────────────────────────────────┘       │
│                           │                                 │
│                    ┌──────┴──────┐                         │
│                    │    Kafka    │                         │
│                    │   Streams   │                         │
│                    └──────┬──────┘                         │
│                           │                                 │
│      ┌────────────────────┼────────────────────┐           │
│      │                    │                    │           │
│  ┌───┴────┐          ┌────┴───┐          ┌────┴───┐       │
│  │ Edge 1 │          │ Edge 2 │          │ Edge N │       │
│  └────────┘          └────────┘          └────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**New Components**:

- **Kafka/Pulsar**: Event streaming for telemetry at scale
- **TimescaleDB**: Time-series optimized storage
- **ML Workers**: Model training and inference
- **Kubernetes**: Auto-scaling, self-healing

### Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Primary solver** | Gurobi | Best performance for QP, cloud API |
| **Fallback solver** | HiGHS | Open source, good enough for most |
| **Edge compute** | Raspberry Pi 4 | Low cost, Linux support, GPIO |
| **Cloud provider** | Hetzner | Cost (1/10 of AWS), EU data residency |
| **Database** | PostgreSQL + TimescaleDB | Proven, time-series optimized |
| **ML framework** | PyTorch | Flexibility, transformer support |
| **Frontend** | React + Vite | Fast, team familiarity |
| **Mobile** | PWA | Single codebase, offline support |

### Integration Roadmap

| Integration | Priority | Timeline | Status |
|-------------|----------|----------|--------|
| DERConnect | P0 | Month 1-2 | In progress |
| Africa GreenTec API | P0 | Month 2-3 | Planned |
| Modbus RTU/TCP | P0 | Month 1 | Built |
| M-Pesa | P1 | Month 4-5 | Planned |
| Orange Money | P1 | Month 5-6 | Planned |
| WhatsApp Business | P1 | Month 3-4 | Planned |
| Meteostat (weather) | P2 | Month 4 | Planned |
| OpenWeatherMap | P2 | Month 4 | Planned |
| SparkMeter | P2 | Month 6-8 | Future |
| IEEE 2030.5 | P3 | Year 2 | Future |

### Cybersecurity Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LAYER 1: NETWORK                                           │
│  • All traffic TLS 1.3                                      │
│  • VPN tunnels for edge devices                             │
│  • IP allowlisting for critical endpoints                   │
│  • DDoS protection (Cloudflare)                             │
│                                                             │
│  LAYER 2: AUTHENTICATION                                    │
│  • JWT with short expiry (15 min)                           │
│  • Refresh token rotation                                   │
│  • MFA for operator accounts                                │
│  • API keys with scope limits                               │
│                                                             │
│  LAYER 3: AUTHORIZATION                                     │
│  • Role-based access control (RBAC)                         │
│  • Tenant isolation (row-level security)                    │
│  • Audit logging (all state changes)                        │
│                                                             │
│  LAYER 4: DATA                                              │
│  • Encryption at rest (AES-256)                             │
│  • Field-level encryption for sensitive data                │
│  • Automated backups (encrypted, geo-redundant)             │
│                                                             │
│  LAYER 5: OPERATIONAL                                       │
│  • Dependency scanning (Snyk/Dependabot)                    │
│  • Container scanning                                       │
│  • Penetration testing (annual)                             │
│  • Incident response plan                                   │
│                                                             │
│  COMPLIANCE TARGET: SOC 2 Type II by Year 2                │
└─────────────────────────────────────────────────────────────┘
```

---

## Next Steps

### This Week (April 12-19, 2026)

**Engineering (40 hours)**

- [ ] **Mon-Tue**: Complete DERConnect integration MVP
  - [ ] Read telemetry from DERConnect test site
  - [ ] Write dispatch commands
  - [ ] Handle connection failures gracefully

- [ ] **Wed**: Edge agent prototype
  - [ ] Raspberry Pi setup script
  - [ ] Modbus polling loop (5-second interval)
  - [ ] Local SQLite buffer for offline

- [ ] **Thu**: API hardening
  - [ ] Add authentication middleware
  - [ ] Rate limiting
  - [ ] Input validation

- [ ] **Fri**: Deployment pipeline
  - [ ] Docker Compose for local dev
  - [ ] Hetzner server provisioned
  - [ ] CI/CD with GitHub Actions

**Business (10 hours)**

- [ ] Send Africa GreenTec pilot proposal (updated with DERConnect timeline)
- [ ] Schedule 3 prospect calls (use existing network)
- [ ] Register domain (kora.energy or similar)
- [ ] Draft one-pager (1 page, problem → solution → results → pricing)

**Deliverable**: Working telemetry pipeline from DERConnect to KORA cloud

---

### This Month (April 2026)

**Week 1 (Apr 12-19)**: See above

**Week 2 (Apr 20-26): Mahavelona Pilot Launch**
- [ ] Deploy edge agent at Mahavelona
- [ ] Verify telemetry flow (PV, battery, loads)
- [ ] Run optimizer in advisory mode (recommend prices, don't execute)
- [ ] Operator training session (virtual)
- [ ] Daily review calls with AGT team

**Week 3 (Apr 27 - May 3): Validation & Iteration**
- [ ] Compare KORA recommendations vs manual decisions
- [ ] Calculate theoretical savings (if KORA had been in control)
- [ ] Identify gaps in optimizer (edge cases, constraints)
- [ ] Implement top 3 fixes
- [ ] Weather API integration (basic forecast)

**Week 4 (May 4-10): Auto Mode Preparation**
- [ ] Safety checks implementation (hard limits on price, SOC)
- [ ] Circuit breaker patterns (fallback to safe state)
- [ ] Alerting (Slack/SMS when anomalies)
- [ ] AGT approval for auto mode transition
- [ ] Switch to auto mode (KORA sets prices)

**Business Milestones**:
- [ ] Africa GreenTec pilot agreement signed
- [ ] 5 prospect calls completed
- [ ] Pitch deck v1 complete
- [ ] Incorporate (Delaware C-Corp if raising US money)
- [ ] Bank account opened

**Deliverable**: Mahavelona running in auto mode with KORA setting prices

---

### This Quarter (Q2 2026: April - June)

**Month 1 (April)**: See above

**Month 2 (May): Second Site + Results**
- [ ] Mahavelona: 30 days of auto-mode data
- [ ] Calculate actual curtailment reduction
- [ ] Calculate actual revenue increase
- [ ] Case study document (with graphs, numbers)
- [ ] Second AGT site onboarding
- [ ] PowerGen first conversation

**Month 3 (June): Scale Preparation**
- [ ] Third AGT site live
- [ ] ML forecasting v1 (demand model)
- [ ] Multi-site dashboard view
- [ ] API documentation
- [ ] Pre-seed fundraising started
- [ ] 10 prospect conversations completed

**Q2 Exit Criteria**:
| Metric | Target |
|--------|--------|
| Sites live | 3 |
| MRR | $1,500 |
| Curtailment (best site) | <20% |
| Documented case study | 1 |
| Pipeline (interested prospects) | 15 |

---

### This Year (2026)

**Q1 (Jan-Mar)**: Foundation *(completed)*
- Simulation system built
- Optimizer proven in testing
- Partnership with AGT and DERConnect

**Q2 (Apr-Jun)**: First Production Sites
- 3 sites live (all AGT)
- First paying customer
- Pre-seed conversations started
- $1,500 MRR

**Q3 (Jul-Sep)**: Pre-Seed & Expansion
- Pre-seed closed ($100-150k)
- 7 sites live
- Second country (Kenya or Rwanda)
- ML forecasting deployed
- $5,000 MRR
- First hire (engineering or customer success)

**Q4 (Oct-Dec)**: Scaling
- 11 sites live
- Third country
- Mobile money integration
- $15,000 MRR
- Seed conversations started

**2026 Exit Criteria**:
| Metric | Target |
|--------|--------|
| Sites live | 11 |
| Countries | 3 |
| MRR | $15,000 |
| ARR | $180,000 |
| Team size | 2-3 |
| Pre-seed raised | $100-150k |
| Avg curtailment | <20% |

---

### Year 2-5 Roadmap

#### Year 2 (2027): Product-Market Fit

**Goal**: Prove unit economics, reach $500k ARR

| Quarter | Sites | MRR | Key Milestone |
|---------|-------|-----|---------------|
| Q1 | 14 | $25k | Seed closed ($750k-1.5M) |
| Q2 | 22 | $35k | 5th country, ML forecasting GA |
| Q3 | 35 | $55k | First enterprise customer |
| Q4 | 50 | $80k | KORA Grid beta |

**Key Hires**: CTO, Head of Customer Success, 2 Engineers
**Total Team**: 7

#### Year 3 (2028): Scale

**Goal**: Dominant position in African microgrids, $2M ARR

| Quarter | Sites | MRR | Key Milestone |
|---------|-------|-----|---------------|
| Q1 | 70 | $110k | KORA Grid GA |
| Q2 | 100 | $150k | Series A ($5-8M) |
| Q3 | 140 | $200k | First non-African market |
| Q4 | 180 | $250k | 10+ countries |

**Key Hires**: VP Sales, 3 Engineers, 2 Customer Success
**Total Team**: 15

#### Year 4 (2029): Expansion

**Goal**: Multi-region, energy trading launch, $5M ARR

| Quarter | Sites | MRR | Key Milestone |
|---------|-------|-----|---------------|
| Q1 | 220 | $320k | India launch |
| Q2 | 280 | $400k | KORA Markets beta |
| Q3 | 350 | $500k | First trading revenue |
| Q4 | 400 | $600k | 20+ countries |

**Key Hires**: VP Engineering, Head of Product, Regional Directors
**Total Team**: 30

#### Year 5 (2030): Platform

**Goal**: Energy trading at scale, $15M ARR, IPO-ready metrics

| Quarter | Sites | MRR | Key Milestone |
|---------|-------|-----|---------------|
| Q1 | 450 | $800k | Series B ($20-30M) |
| Q2 | 550 | $1M | Developed market entry |
| Q3 | 650 | $1.2M | KORA OS beta |
| Q4 | 750 | $1.5M | $15M+ ARR |

**Total Team**: 60+

---

## Execution Checklist

### Immediate (This Week)

**Engineering**
- [ ] DERConnect telemetry integration
- [ ] Edge agent v0.1 (Raspberry Pi)
- [ ] API authentication
- [ ] Hetzner deployment
- [ ] CI/CD pipeline

**Business**
- [ ] Send AGT pilot proposal
- [ ] Schedule 3 prospect calls
- [ ] Register domain
- [ ] Draft one-pager

### Short-Term (This Month)

**Engineering**
- [ ] Mahavelona edge agent deployed
- [ ] Advisory mode running
- [ ] Auto mode with safety checks
- [ ] Weather API integration
- [ ] Alerting system (SMS/Slack)

**Business**
- [ ] AGT pilot agreement signed
- [ ] 5 prospect calls completed
- [ ] Pitch deck v1
- [ ] Incorporate company
- [ ] Bank account

### Medium-Term (This Quarter)

**Product**
- [ ] 3 sites in production
- [ ] ML demand forecasting v1
- [ ] Multi-site dashboard
- [ ] Mobile-responsive PWA
- [ ] API documentation

**Business**
- [ ] First paying customer
- [ ] $1,500 MRR
- [ ] Case study published
- [ ] Pre-seed fundraising started
- [ ] 15 prospects in pipeline

### 12-Month Milestones

**Q2 2026**: First Production
- [ ] 3 sites live
- [ ] $1,500 MRR
- [ ] Case study complete

**Q3 2026**: Pre-Seed
- [ ] $100-150k raised
- [ ] 7 sites live
- [ ] Second country
- [ ] $5,000 MRR

**Q4 2026**: Scale
- [ ] 11 sites live
- [ ] Third country
- [ ] $15,000 MRR
- [ ] Mobile money integration

**Q1 2027**: Seed Ready
- [ ] 14 sites live
- [ ] $25,000 MRR
- [ ] Seed term sheets

---

## Risks & Mitigations

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Optimizer fails in production** | Medium | High | Failsafe mode, health checks, gradual rollout |
| **Connectivity issues (rural)** | High | Medium | Edge caching, offline mode, async sync |
| **Hardware incompatibility** | Medium | Medium | DERConnect abstraction, extensive testing |
| **Gurobi licensing cost** | Low | Medium | HiGHS fallback, negotiate academic rate |
| **Security breach** | Low | Critical | SOC 2 prep, pen testing, encryption |

### Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Slow customer adoption** | Medium | High | Land and expand, performance guarantees |
| **AGT pilot fails** | Low | High | Daily monitoring, backup pilot prospects |
| **Competition** | Medium | Medium | Move fast, build relationships, vertical focus |
| **Funding gap** | Medium | High | Bootstrap longer, grant funding, revenue focus |
| **Key person risk (solo founder)** | High | Critical | Find co-founder, document everything |

### Market Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Mini-grid market stalls** | Low | High | Diversify to C&I, grid-connected |
| **Regulatory changes** | Low | Medium | Country diversification, compliance focus |
| **Currency volatility** | High | Medium | USD pricing, hedging, local costs local currency |
| **Political instability** | Medium | Medium | Multi-country presence, cloud infrastructure |

---

## Financial Projections

### 5-Year P&L Summary

| Year | Sites | ARR | Gross Margin | Team | Burn | Status |
|------|-------|-----|--------------|------|------|--------|
| 2026 | 11 | $180k | 80% | 3 | $200k | Pre-seed |
| 2027 | 50 | $600k | 82% | 7 | $700k | Seed |
| 2028 | 180 | $2.4M | 83% | 15 | $2M | Series A |
| 2029 | 400 | $6M | 84% | 30 | $4M | Scaling |
| 2030 | 750 | $15M | 85% | 60 | $8M | Series B |

### Funding Strategy

**Pre-Seed ($100-150k) - Q3 2026**
- Sources: Angels, Catalyst Fund, GSMA Innovation Fund
- Use: MVP completion, pilot expansion, first hire
- Runway: 9-12 months

**Seed ($750k-1.5M) - Q1 2027**
- Sources: Energy Access Ventures, Factor[e], Congruent
- Use: Team (60%), expansion (25%), product (15%)
- Runway: 18 months

**Series A ($5-8M) - Q2 2028**
- Sources: Climate VCs, emerging market specialists
- Use: Scale engineering, go-to-market, international
- Runway: 24 months

---

## Key Partnerships

### Strategic Partners

| Partner | Type | Value | Status |
|---------|------|-------|--------|
| **Africa GreenTec** | Anchor customer | First sites, references, introductions | Active pilot |
| **DERConnect (UCSD)** | Technical | Hardware abstraction, credibility | Partnership signed |
| **PowerGen** | Customer | Kenya entry, 100+ sites potential | Target |
| **Energy Access Ventures** | Investor | Introductions, board support | Target |

### Integration Partners

| Partner | Integration | Timeline |
|---------|-------------|----------|
| Victron | Modbus integration | Q2 2026 |
| SMA | SunSpec integration | Q3 2026 |
| SparkMeter | API integration | Q4 2026 |
| M-Pesa | Payment API | Q3 2026 |

---

## Appendix A: Feature Detailed Roadmap

### KORA Core Features (Year 1)

| Feature | Description | Status | ETA |
|---------|-------------|--------|-----|
| Real-time optimization | 15-min dispatch scheduling | Built | Now |
| Dynamic pricing | Price-responsive demand | Built | Now |
| Battery dispatch | Charge/discharge optimization | Built | Now |
| Operator dashboard | Mobile-first monitoring | Built | Now |
| Advisory mode | Recommendations without execution | Building | Apr 2026 |
| Auto mode | Autonomous operation | Building | May 2026 |
| Edge agent | On-site data collection | Building | Apr 2026 |
| Basic forecasting | Persistence + weather | Planned | May 2026 |
| SMS alerts | Operator notifications | Planned | May 2026 |
| WhatsApp integration | Customer price alerts | Planned | Jun 2026 |
| CSV export | Historical data export | Built | Now |
| Multi-tenant | Site isolation | Built | Now |

### KORA Intelligence Features (Year 2)

| Feature | Description | Priority | ETA |
|---------|-------------|----------|-----|
| ML demand forecasting | Site-specific models | P0 | Q3 2026 |
| Solar nowcasting | Satellite-based prediction | P1 | Q4 2026 |
| Anomaly detection | Automated alerts | P1 | Q4 2026 |
| Predictive maintenance | Failure prediction | P2 | Q1 2027 |
| Portfolio analytics | Cross-site insights | P1 | Q1 2027 |
| API v2 | GraphQL, webhooks | P1 | Q2 2027 |
| White-label | Branded for partners | P2 | Q2 2027 |

### KORA Grid Features (Year 2-3)

| Feature | Description | Priority | ETA |
|---------|-------------|----------|-----|
| Multi-site optimization | Regional dispatch | P0 | Q3 2027 |
| Energy sharing | Inter-site flows | P1 | Q4 2027 |
| Demand aggregation | Portfolio DR programs | P1 | Q4 2027 |
| Grid-connected mode | Import/export optimization | P1 | Q1 2028 |
| VPP capabilities | Grid services | P2 | Q2 2028 |

### KORA Markets Features (Year 3-5)

| Feature | Description | Priority | ETA |
|---------|-------------|----------|-----|
| P2P trading | Energy marketplace | P1 | Q3 2028 |
| Wholesale integration | Market participation | P2 | Q1 2029 |
| Carbon marketplace | Credit automation | P2 | Q2 2029 |
| Financial settlement | Automated billing | P1 | Q4 2028 |

---

## Appendix B: Standards & Compliance Roadmap

### Communication Standards

| Standard | Purpose | Priority | Timeline |
|----------|---------|----------|----------|
| Modbus RTU/TCP | Inverter/meter communication | P0 | Built |
| SunSpec | Solar equipment interop | P1 | Q3 2026 |
| IEEE 2030.5 | DER communication | P2 | Year 2 |
| OpenADR | Demand response | P2 | Year 2 |
| IEC 61850 | Substation automation | P3 | Year 3 |

### Security & Compliance

| Standard | Purpose | Priority | Timeline |
|----------|---------|----------|----------|
| SOC 2 Type I | Security baseline | P1 | Q4 2027 |
| SOC 2 Type II | Ongoing compliance | P1 | Q2 2028 |
| ISO 27001 | Information security | P2 | Year 3 |
| GDPR | EU data protection | P1 | Q3 2027 |
| NERC CIP (lite) | Grid cybersecurity | P3 | Year 4 |

---

## Appendix C: Team Building Plan

### Year 1 Hires (3 people)

1. **CTO / Technical Co-founder** (Q2-Q3 2026)
   - Owns architecture, leads engineering
   - Experience: 10+ years, distributed systems, energy a plus
   - Compensation: 5-15% equity, $80-120k salary

2. **Head of Customer Success** (Q3 2026)
   - Owns operator relationships, onboarding
   - Experience: 5+ years, energy/Africa experience
   - Compensation: 1-3% equity, $60-80k salary

3. **Backend Engineer** (Q4 2026)
   - Optimizer, integrations, API
   - Experience: 3+ years, Python, systems
   - Compensation: 0.5-1% equity, $70-100k salary

### Year 2 Hires (4 people)

4. Technical Support (in-country)
5. Full-Stack Engineer
6. Implementation Specialist
7. Partnership Manager

### Founding Team Gaps to Fill

| Role | Gap | Urgency |
|------|-----|---------|
| Technical co-founder | Architecture, scaling | High |
| Africa operator | On-ground presence | High |
| Sales leader | Enterprise motion | Medium |
| ML engineer | Forecasting models | Medium |

---

*This is a living document. Review monthly, update quarterly.*

*Next review: May 12, 2026*