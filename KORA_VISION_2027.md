# KORA: Year 1 Vision (February 2027)

> This document defines success for KORA. Every feature, every hire, every decision should move us toward this.

---

## The Numbers

| Metric | Now (Feb 2026) | Year 1 Target |
|--------|----------------|---------------|
| Sites Live | 1 (Mahavelona pilot) | 14 |
| Customers Served | 251 | 4,200+ |
| Average Curtailment | 70% | 8% |
| Monthly Recurring Revenue | $0 | $42,000 |
| Team Size | 1 | 7 |
| Countries | 1 | 4 |

---

## Mahavelona: The Proof Point

**Before KORA:**
- Battery full by 10am, 70% solar curtailed
- Evening blackouts 2-3x/week
- Revenue: 180,000 Ar/day (~$38)

**After KORA (Target):**
- Curtailment: 6-9%
- Zero unplanned blackouts
- Revenue: 485,000 Ar/day (~$102) - **2.7x increase**
- Customer satisfaction: 94%+

---

## Product Tiers

### KORA Core ($200/month + $0.02/kWh)
- Real-time optimization
- Dynamic pricing
- Battery dispatch
- Basic dashboards
- SMS notifications

### KORA Pro ($400/month + $0.015/kWh)
- Everything in Core
- ML forecasting (site-specific models)
- Multi-site portfolio view
- API access
- Priority support

### KORA Enterprise (Custom, ~$15-25k/year for 10-20 sites)
- Everything in Pro
- Dedicated instance
- Custom model training
- White-label option

---

## Technical Architecture (Target State)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Site Edge     │     │   KORA Cloud    │     │   Operator      │
│   (Raspberry Pi)│────▶│   (AWS/Hetzner) │◀────│   Dashboard     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
   DERConnect              PostgreSQL              React PWA
   Modbus RTU              TimescaleDB            Mobile-first
   Local cache             Redis                  Offline-capable
   Failsafe mode           Gurobi Cloud
                           Python workers
```

### Key Technical Milestones

1. **Edge Computing** - Raspberry Pi agent at each site
   - Local telemetry collection (5-second intervals)
   - Offline caching when internet drops
   - Failsafe mode with last-known schedule

2. **TimescaleDB Migration** - For time-series at scale
   - Handle 500M+ telemetry points
   - 10x compression
   - Fast historical queries

3. **ML Forecasting Suite**
   - Site-specific PV models
   - Demand clustering
   - Anomaly detection

4. **PWA Dashboard**
   - Works offline
   - Push notifications
   - Mobile-first design

---

## Integrations Roadmap

| Integration | Priority | Status | Notes |
|-------------|----------|--------|-------|
| DERConnect | P0 | In Progress | Telemetry from SMA/Victron |
| Africa GreenTec API | P0 | Planned | Customer data, billing sync |
| M-Pesa | P1 | Planned | Mobile money (Kenya) |
| Orange Money | P1 | Planned | Mobile money (Madagascar) |
| WhatsApp Business | P1 | Planned | Price alerts |
| Meteostat | P2 | Planned | Weather forecasts |
| MTN MoMo | P2 | Future | Mobile money (Uganda, Ghana) |

---

## Team Structure (Year 1)

```
CEO/Founder (You)
├── CTO
│   ├── Backend Engineer
│   └── Full-Stack Engineer
├── Head of Customer Success
│   ├── Technical Support (in-country)
│   └── Implementation Specialist
└── Head of Growth
    └── Partnership Manager
```

### Key Hires (In Order)
1. **CTO/Technical Co-founder** - Owns architecture, leads engineering
2. **Head of Customer Success** - Owns operator relationships
3. **Backend Engineer** - Optimizer, integrations
4. **Technical Support** - Based in Nairobi or Antananarivo
5. **Full-Stack Engineer** - Dashboard, mobile
6. **Implementation Specialist** - Onboarding new sites
7. **Partnership Manager** - Africa GreenTec + new partners

---

## Geographic Expansion

### Phase 1: Madagascar (Months 1-6)
- 6 sites with Africa GreenTec
- Local support staff in Antananarivo
- Regulatory relationships established

### Phase 2: Kenya (Months 4-9)
- 4 sites with PowerGen
- M-Pesa integration
- Nairobi office (2 people)

### Phase 3: Rwanda (Months 7-12)
- 2 sites with BBOXX
- Government relationship through REG

### Phase 4: Nigeria (Months 9-12)
- 2 pilot sites with Husk Power
- Currency risk management

---

## Funding Milestones

### Pre-Seed ($150k) - Target: Month 3
- Angels, Catalyst Fund, GSMA
- Use: MVP completion, Mahavelona results

### Seed ($750k) - Target: Month 8
- Energy Access Ventures, Factor[e]
- Use: Team (60%), expansion (20%), product (15%)

---

## Unit Economics (Target)

```
Average Site (Monthly)
─────────────────────────────────────────────────
Energy throughput:           15,000 kWh
Subscription:                $300
Performance fee:             $225 (@ $0.015/kWh)
─────────────────────────────────────────────────
Total revenue:               $525/site

Cost to serve:
  Cloud:                     $15
  Support:                   $40
  Customer success:          $25
─────────────────────────────────────────────────
Gross margin:                ~85%
─────────────────────────────────────────────────
```

---

## Competitive Positioning

**Win on:**
1. **Results** - Curtailment reduction numbers unmatched
2. **Hardware-agnostic** - Work with any inverter/battery
3. **Software-only** - No capex, just opex
4. **African-first** - Team on the ground
5. **Open** - API-first, integrate with existing systems

**Competitors:**
- SparkMeter (hardware-centric, less optimization)
- SteamaCo (acquired by Husk)
- Odyssey Energy Solutions (portfolio mgmt, less real-time)

---

## Key Partnerships

### Africa GreenTec (Anchor)
- Original pilot partner
- Equity investor ($50k in seed)
- 6 sites deployed
- Introductions to other developers

### DERConnect (Technical)
- Full telemetry integration
- Listed in partner directory
- Co-marketing

### Energy Access Ventures (Investor)
- Board observer seat
- Introductions to 15+ developers
- Hiring support

---

## Impact Targets (Year 1)

| Metric | Target |
|--------|--------|
| Additional clean energy utilized | 1.2 GWh/year |
| CO2 avoided | 850 tons/year |
| Blackout hours prevented | 4,200 hours |
| Households with improved electricity | 3,800 |
| SMEs with reliable power | 340 |
| Schools & clinics with 24/7 power | 45 |

---

## Quarterly Milestones

### Q1 2026
- [ ] Mahavelona live with real telemetry
- [ ] Curtailment below 30%
- [ ] First paying customer (Africa GreenTec)
- [ ] DERConnect integration complete

### Q2 2026
- [ ] 3 sites live
- [ ] $2,100 MRR
- [ ] Pre-seed closed
- [ ] CTO hired

### Q3 2026
- [ ] 7 sites live
- [ ] Kenya launch (PowerGen)
- [ ] $8,400 MRR
- [ ] Mobile money integration

### Q4 2026
- [ ] 11 sites live
- [ ] Rwanda launch
- [ ] $18,500 MRR
- [ ] Seed round closed

### Q1 2027
- [ ] 14 sites live
- [ ] Nigeria pilots
- [ ] $42,000 MRR
- [ ] Team of 7

---

## Decision Principles

1. **Results > Features** - Ship what improves curtailment
2. **Operators first** - Design for the site manager
3. **Local presence** - Hire in-country before scaling
4. **Prove then expand** - 2 sites working before adding country
5. **Simple then smart** - Linear optimizer first, ML later

---

## What Success Feels Like

> "They took a microgrid that was wasting 70% of its energy and turned it into a model site that Africa GreenTec now showcases to every investor."

The welding shop owner in Mahavelona works 8 hours instead of 3. The clinic's vaccine fridge never fails. The rice miller processes twice as much grain.

KORA is no longer a promise - it's a track record.

---

*Last updated: February 2026*
*Next review: Monthly*
