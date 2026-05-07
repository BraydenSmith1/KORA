# KORA Execution Tracker
## Week-by-Week Action Items

> Update this document as you complete items. Mark [x] when done.

---

## THIS WEEK: April 12-19, 2026

### Engineering (Priority Order)

**Monday-Tuesday: DERConnect Integration**
- [ ] Get DERConnect test credentials from UCSD team
- [ ] Read telemetry (PV power, battery SOC, load) from test inverter
- [ ] Write setpoints (price signal, battery dispatch command)
- [ ] Handle disconnection gracefully (retry with exponential backoff)
- [ ] Log all communications for debugging

**Wednesday: Edge Agent Prototype**
- [ ] Create `edge-agent/` directory with Python project
- [ ] Implement Modbus RTU/TCP polling (5-second interval)
- [ ] Local SQLite buffer for offline operation
- [ ] HTTPS POST to cloud API when connected
- [ ] Raspberry Pi setup script (install deps, systemd service)

**Thursday: API Hardening**
- [ ] Add JWT authentication middleware to Express
- [ ] Implement rate limiting (100 req/min/IP)
- [ ] Input validation (Joi or Zod schemas)
- [ ] Error handling middleware (structured responses)
- [ ] Add request logging (correlation IDs)

**Friday: Deployment Pipeline**
- [ ] Docker Compose file for local development
- [ ] Provision Hetzner VPS (CX31 or similar)
- [ ] GitHub Actions workflow: test → build → deploy
- [ ] Environment variable management (.env.production)
- [ ] SSL certificate (Let's Encrypt via Caddy)

### Business

- [ ] **Africa GreenTec**: Send updated pilot proposal with specific timeline
  - Include: DERConnect integration plan, Mahavelona deployment date
  - Ask for: Technical contact, Modbus register map, site access date

- [ ] **Prospect Outreach**: Schedule 3 calls
  - PowerGen (Kenya): Ask DERConnect for intro
  - Husk Power: LinkedIn cold outreach to CTO
  - BBOXX: Conference connection follow-up

- [ ] **Domain**: Register kora.energy (or kora.io, koraenergy.com)

- [ ] **One-Pager**: Draft v1
  - Problem (70% curtailment, $85/day wasted)
  - Solution (AI optimization, dynamic pricing)
  - Results (70%→9% curtailment, 3x revenue)
  - Pricing ($300-500/site/month)

### Deliverables by Friday

| Deliverable | Done |
|-------------|------|
| DERConnect reads real telemetry | [ ] |
| Edge agent runs on Raspberry Pi | [ ] |
| API deployed to Hetzner | [ ] |
| CI/CD pipeline working | [ ] |
| AGT proposal sent | [ ] |
| 3 prospect calls scheduled | [ ] |

---

## WEEK 2: April 20-26, 2026

### Engineering: Mahavelona Pilot Launch

- [ ] Ship Raspberry Pi to Madagascar (or have AGT procure locally)
- [ ] Remote setup session with AGT technician
- [ ] Verify Modbus connection to SMA/Victron equipment
- [ ] Confirm telemetry appearing in KORA dashboard
- [ ] Run optimizer in **advisory mode** (display recommendations only)
- [ ] Compare recommendations vs actual operator decisions
- [ ] Daily sync with AGT team (15 min call)

### Business

- [ ] AGT pilot agreement signed (if not done Week 1)
- [ ] 2 more prospect calls completed
- [ ] Start pitch deck (10 slides)
- [ ] Research incorporation options (Delaware vs Wyoming)

---

## WEEK 3: April 27 - May 3, 2026

### Engineering: Validation

- [ ] Calculate: If KORA had been in control, what would savings be?
- [ ] Identify top 3 optimizer gaps (edge cases, constraints)
- [ ] Implement fixes for identified issues
- [ ] Basic weather forecast integration (OpenWeatherMap)
- [ ] Improve demand response model based on real data

### Business

- [ ] Pitch deck complete (v1)
- [ ] Case study draft (even if preliminary data)
- [ ] Incorporate company
- [ ] Open business bank account (Mercury or similar)

---

## WEEK 4: May 4-10, 2026

### Engineering: Auto Mode

- [ ] Safety checks: Hard limits on price (never below X, above Y)
- [ ] Safety checks: Battery SOC limits (never below 20%)
- [ ] Circuit breaker: If solver fails, revert to fixed pricing
- [ ] Alerting: Slack/SMS when anomalies detected
- [ ] Get AGT sign-off for auto mode transition
- [ ] **GO LIVE**: KORA sets prices automatically

### Business

- [ ] Celebrate going live (social media post?)
- [ ] Begin tracking daily metrics (curtailment %, revenue)
- [ ] Follow up with all prospects
- [ ] Identify 5 more prospects

---

## MONTH 2: May 2026

### Week 5-6: Data Collection & Second Site

- [ ] 14+ days of auto-mode data
- [ ] Calculate actual curtailment reduction
- [ ] Calculate actual revenue increase
- [ ] Start onboarding second AGT site
- [ ] PowerGen: First call completed

### Week 7-8: ML Forecasting V1

- [ ] Train basic demand model on Mahavelona data
- [ ] Deploy model to production
- [ ] Compare forecast vs actual demand
- [ ] Case study document with real numbers
- [ ] Third AGT site identified

---

## MONTH 3: June 2026

### Focus: Pre-Seed & Expansion

- [ ] Third site live
- [ ] 30-day results documented
- [ ] Multi-site dashboard view (portfolio)
- [ ] Pre-seed fundraising: First investor meetings
- [ ] Grant applications submitted (GSMA, Catalyst Fund)
- [ ] 10+ prospect conversations completed

### Month 3 Exit Criteria

| Metric | Target | Actual |
|--------|--------|--------|
| Sites live | 3 | |
| Avg curtailment | <25% | |
| MRR | $1,500 | |
| Pipeline | 15 prospects | |

---

## Q2 2026 (Apr-Jun) Summary Goals

| Metric | Target |
|--------|--------|
| Sites live | 3 |
| Countries | 1 |
| MRR | $1,500 |
| Curtailment (best site) | <20% |
| Case study | Published |
| Pipeline | 15 qualified leads |
| Incorporation | Complete |

---

## Q3 2026 (Jul-Sep) Goals

| Metric | Target |
|--------|--------|
| Sites live | 7 |
| Countries | 2 |
| MRR | $5,000 |
| Pre-seed closed | $100-150k |
| First hire | Made |
| ML forecasting | Deployed |

---

## Q4 2026 (Oct-Dec) Goals

| Metric | Target |
|--------|--------|
| Sites live | 11 |
| Countries | 3 |
| MRR | $15,000 |
| Mobile money | Integrated |
| Seed conversations | Started |

---

## Key Contacts & Follow-Ups

### Africa GreenTec
- **Main contact**: [Name]
- **Technical contact**: [Name]
- **Last contact**:
- **Next action**: Send pilot proposal
- **Notes**:

### PowerGen
- **Contact needed**: CTO or VP Engineering
- **Intro path**: DERConnect / AMDA conference
- **Next action**: Request intro from DERConnect
- **Notes**: 100+ sites in Kenya/Tanzania

### Husk Power
- **Contact needed**: CTO
- **Intro path**: Cold LinkedIn
- **Next action**: Send connection request
- **Notes**: 200+ sites India/Nigeria

### BBOXX
- **Contact needed**: Mini-grid product lead
- **Intro path**: ARE conference connection
- **Next action**: Follow up on conference conversation
- **Notes**: Expanding from SHS to mini-grids

### DERConnect (UCSD)
- **Main contact**: [Name]
- **Last contact**:
- **Next action**: Get test credentials
- **Notes**: Partnership signed

---

## Daily Standup Template

**Date**: ___________

**Yesterday**:
-

**Today**:
-

**Blockers**:
-

**Key Metric Update**:
- Curtailment %:
- Revenue:
- Sites live:

---

## Weekly Review Template

**Week of**: ___________

### Wins
1.
2.
3.

### Misses
1.
2.

### Learnings
1.
2.

### Next Week Top 3
1.
2.
3.

### Metrics
| Metric | Last Week | This Week | Change |
|--------|-----------|-----------|--------|
| Sites live | | | |
| Curtailment % | | | |
| MRR | | | |
| Pipeline | | | |

---

## Important Links

- **Production Dashboard**: [URL]
- **GitHub Repo**: [URL]
- **Hetzner Console**: [URL]
- **Gurobi Cloud**: [URL]
- **DERConnect Portal**: [URL]
- **CRM (HubSpot)**: [URL]
- **Bank (Mercury)**: [URL]

---

## Quick Reference: Key Technical Tasks

### To Deploy New Site

1. Provision Raspberry Pi with edge agent
2. Get Modbus register map from equipment vendor
3. Configure site in KORA dashboard
4. Deploy edge agent via SSH
5. Verify telemetry flowing
6. Run 48 hours in advisory mode
7. Review with operator
8. Enable auto mode

### To Debug Optimizer

1. Check solver logs: `python-optimizer/logs/`
2. Check constraints satisfied: `kora_tester.py --scenario baseline`
3. Check telemetry: Dashboard → Site → Raw Data
4. Check edge agent: SSH to Pi, `journalctl -u kora-agent`

### To Add New Integration

1. Create adapter in `api/src/lib/integrations/`
2. Implement `connect()`, `read()`, `write()` methods
3. Add to device registry
4. Test with DERConnect simulator
5. Document in API docs

---

*Last updated: April 12, 2026*