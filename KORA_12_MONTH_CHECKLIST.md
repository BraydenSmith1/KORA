# Kora 12-Month Execution Checklist

**Start Date**: February 2025
**Goal**: 25-35 paying customers, $100-150K ARR, $1.5-2.5M Seed raised

---

## Q1: Foundation (Feb - Apr 2025)

### 1. Product & Engineering

#### 1.1 Production-Ready Optimizer
- [x] Error handling & recovery
  - [x] Modbus connection retry logic
  - [x] Solver failure fallback modes
  - [x] Bad data detection and handling
  - [x] Alerting system for failures
- [x] Configuration management
  - [x] YAML/JSON config system for site parameters
  - [x] Config validation on startup
  - [x] Example configs for common setups
- [x] Logging & observability
  - [x] Structured logging (JSON format)
  - [x] Log levels (DEBUG, INFO, WARN, ERROR)
  - [ ] Log aggregation setup (Axiom/Logflare)
- [x] Solver reliability
  - [x] Test suite with 50+ scenarios
  - [x] Cloudy day scenarios
  - [x] Battery failure scenarios
  - [x] Demand spike scenarios
  - [x] Edge case handling
- [x] Performance optimization
  - [x] Profile solver performance
  - [x] Optimize for <30 second solve time
  - [ ] Add result caching where appropriate

#### 1.2 Operator Dashboard (Production)
- [x] Authentication
  - [x] JWT-based authentication
  - [x] User registration
  - [x] Password reset flow
  - [x] Session management
- [x] Multi-tenant support
  - [x] Site selector in UI
  - [x] Data isolation between tenants
  - [x] User-to-site permissions
- [x] Real-time updates
  - [x] WebSocket or SSE for live data
  - [x] Live metrics display
  - [x] Connection status indicator
- [x] Mobile responsive
  - [x] Responsive CSS
  - [x] Touch-friendly controls
  - [x] Mobile navigation
- [x] Alerting UI
  - [x] Alert panel
  - [ ] Notification system
  - [x] Alert history
- [ ] Historical data
  - [ ] Date range selector
  - [ ] Trend charts
  - [ ] Period comparisons (today vs last week)
- [x] Export functionality
  - [x] CSV export
  - [ ] PDF report generation

#### 1.3 Deployment Infrastructure
- [x] Cloud deployment
  - [x] Choose platform (Railway/Render/Fly.io)
  - [ ] Automated deploy pipeline
  - [x] Environment variables configured
- [x] Database migration
  - [x] PostgreSQL setup
  - [x] Prisma migration scripts
  - [x] Data migration from SQLite
- [ ] Environment management
  - [ ] Dev/staging/prod separation
  - [x] Secrets management
- [ ] Backup system
  - [ ] Automated daily backups
  - [ ] Backup to S3/B2
  - [ ] Restore procedure documented
- [ ] Uptime monitoring
  - [ ] UptimeRobot or Better Uptime setup
  - [ ] Alert notifications configured

---

### 2. Sales & Business Development

#### 2.1 Target Customer Identification
- [ ] Build prospect list (100+ contacts)
  - [ ] Mini-grid developers Africa (30 companies)
  - [ ] Mini-grid developers Asia (20 companies)
  - [ ] C&I solar+storage (50 companies)
  - [ ] Island utilities (15 utilities)
- [ ] Set up CRM (HubSpot free tier)
- [ ] Research top 20 prospects (1-page brief each)
- [ ] Identify warm intro paths (10+ requests sent)
- [ ] Cold outreach campaign (50 emails sent)

#### 2.2 Sales Materials
- [ ] One-pager (problem, solution, results, pricing)
- [ ] Pitch deck (10 slides)
- [ ] Case study (Africa GreenTec / Mahavelona)
- [ ] Demo video (3 minutes)
- [ ] ROI calculator (Google Sheet or web tool)
- [ ] Pricing page on website

#### 2.3 First Customer Conversations
- [ ] Africa GreenTec pilot proposal sent
- [ ] Africa GreenTec pilot started
- [ ] 30 prospect conversations completed
- [ ] 5-10 prospects interested in pilot
- [ ] 3-5 signed contracts

---

### 3. Company Building

#### 3.1 Legal & Corporate
- [ ] Incorporate (Delaware C-Corp)
- [ ] Operating agreement (if co-founders)
- [ ] IP assignment to company
- [ ] Terms of service
- [ ] Privacy policy
- [ ] Contractor agreements template

#### 3.2 Financial Infrastructure
- [ ] Business bank account (Mercury/Brex)
- [ ] Accounting software (QuickBooks/Xero)
- [ ] Invoicing system (Stripe Billing)
- [ ] Expense tracking setup
- [ ] Financial model (3-year projections)

#### 3.3 Brand & Web Presence
- [ ] Domain secured (kora.energy or similar)
- [ ] Logo designed
- [ ] Landing page website
- [ ] LinkedIn company page
- [ ] Email domain (you@kora.energy)

---

### Q1 Success Metrics
- [ ] Production deployments: 2-3 sites
- [ ] Paying customers: 3-5
- [ ] MRR: $1,000-2,500
- [ ] Pipeline: 30+ qualified leads
- [ ] Uptime: >99%
- [ ] Customer satisfaction: No churn

---

## Q2: First Customers (May - Jul 2025)

### 1. Product & Engineering

#### 1.1 Customer-Driven Features
- [ ] SMS/WhatsApp alerts for operators
- [ ] Demand response notifications for customers
- [ ] Weather forecast integration
- [ ] Manual override capability
- [ ] Audit log ("Why did Kora set this price?")
- [ ] API for third-party integration

#### 1.2 Reliability & Scale
- [ ] Automated testing (CI/CD)
- [ ] Load testing (simulate 50 sites)
- [ ] Disaster recovery plan
- [ ] Data retention policy
- [ ] Security audit (basic pen testing)

#### 1.3 Analytics & Insights
- [ ] Usage analytics (PostHog)
- [ ] Customer health scoring
- [ ] Aggregate dashboard (all sites)
- [ ] Benchmark reports

---

### 2. Sales & Growth

#### 2.1 Scale What's Working
- [ ] Double down on winning segment
- [ ] Referral program launched
- [ ] 1-2 conferences attended
- [ ] 2 blog posts/month

#### 2.2 Pricing Optimization
- [ ] Test higher prices ($500/month)
- [ ] Annual contract option (20% discount)
- [ ] Usage-based pricing component
- [ ] Enterprise tier defined

#### 2.3 Geographic Expansion
- [ ] East Africa market entry
- [ ] South Asia market entry
- [ ] Caribbean market entry

---

### 3. Fundraising Preparation

#### 3.1 Seed Round Materials
- [ ] Investor deck (15-20 slides)
- [ ] Financial model with assumptions
- [ ] Data room organized
- [ ] 2-3 customer references confirmed
- [ ] Demo environment ready

#### 3.2 Investor Targeting
- [ ] List of 50+ potential investors
- [ ] Climate/Energy VCs identified
- [ ] Emerging market VCs identified
- [ ] Angel investors identified
- [ ] Grant opportunities identified

---

### 4. Team

#### 4.1 First Hire
- [ ] Job description written
- [ ] Posted on climate tech job boards
- [ ] 20+ candidates reviewed
- [ ] 5+ interviews conducted
- [ ] Offer extended and accepted

---

### Q2 Success Metrics
- [ ] Paying customers: 15-25
- [ ] MRR: $5,000-10,000
- [ ] Net revenue retention: >100%
- [ ] Countries: 4-5
- [ ] Team size: 2-3
- [ ] Investor conversations: 20+

---

## Q3: Scale & Fundraise (Aug - Oct 2025)

### 1. Fundraising Execution

#### 1.1 Launch Sequence
- [ ] Deck feedback from 5-10 friendly investors
- [ ] Pitch practiced 10+ times
- [ ] 3-5 meetings per week (weeks 3-6)
- [ ] Weekly updates to interested investors
- [ ] Term sheet(s) received
- [ ] Lead investor selected
- [ ] Due diligence completed
- [ ] Legal docs signed
- [ ] Funds wired

#### 1.2 Fundraising Targets
- [ ] Amount raised: $1.5-2.5M
- [ ] Valuation: $8-12M post-money
- [ ] Lead investor secured

---

### 2. Product: Kora Grid (V1)

#### 2.1 Multi-Site Dashboard
- [ ] Portfolio view (all sites)
- [ ] Comparative analytics
- [ ] Aggregate metrics
- [ ] Cross-portfolio alerts

#### 2.2 Cross-Site Optimization
- [ ] Literature review completed
- [ ] Architecture design documented
- [ ] 2-site prototype working

---

### 3. Sales: Scale

#### 3.1 Sales Process
- [ ] Sales playbook documented
- [ ] CRM properly configured
- [ ] Sales metrics tracked
- [ ] Pricing documentation complete

#### 3.2 Channel Partnerships
- [ ] 1+ hardware distributor partnership
- [ ] 1+ project developer partnership
- [ ] 1+ financing platform partnership

#### 3.3 Inbound Marketing
- [ ] SEO: 500 organic visits/month
- [ ] LinkedIn: 1,000 followers
- [ ] Newsletter: 500 subscribers
- [ ] Webinars: 50 attendees each

---

### 4. Team Scaling (Post-Fundraise)

- [ ] Senior Engineer #2 hired
- [ ] Sales Rep hired
- [ ] Customer Success hired
- [ ] Data Scientist hired (stretch)

---

### Q3 Success Metrics
- [ ] Capital raised: $1.5-2.5M
- [ ] Paying customers: 25-35
- [ ] MRR: $10,000-15,000
- [ ] Team size: 4-6
- [ ] Kora Grid prototype: Working demo

---

## Q4: Growth Mode (Nov 2025 - Jan 2026)

### 1. Product: Production Scale

#### 1.1 Platform Hardening
- [ ] Multi-region deployment
- [ ] Auto-scaling implemented
- [ ] SOC 2 preparation started
- [ ] White-label option available

#### 1.2 Advanced Features
- [ ] ML-based demand forecasting
- [ ] Weather API integration
- [ ] Battery degradation modeling
- [ ] Grid-connected mode support

#### 1.3 Kora Grid V1 Launch
- [ ] Beta with 2-3 portfolio operators
- [ ] Pricing model finalized
- [ ] Production launch (GA)

---

### 2. Sales: Enterprise Motion

#### 2.1 Larger Deals
- [ ] First $5K+/month deal closed
- [ ] Enterprise requirements documented
- [ ] SLA templates ready
- [ ] Security questionnaire responses prepared

#### 2.2 Target Accounts
- [ ] Engie PowerCorner conversation
- [ ] Husk Power Systems conversation
- [ ] PowerGen conversation
- [ ] Yoma Micro Power conversation

---

### 3. Geographic Expansion

- [ ] India market entry (hire or partner)
- [ ] Nigeria market entry (partner)
- [ ] Philippines market entry
- [ ] Currency support added
- [ ] Localization (French for West Africa)

---

### Q4 Success Metrics
- [ ] Paying customers: 35-50
- [ ] ARR: $120,000-180,000
- [ ] Countries: 6-8
- [ ] Team size: 6-8
- [ ] Kora Grid customers: 3-5
- [ ] Net revenue retention: >110%

---

## Year-End Summary Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| Paying customers | 35-50 | [ ] |
| ARR | $150,000+ | [ ] |
| Countries | 6-8 | [ ] |
| Team size | 6-8 | [ ] |
| Seed raised | $1.5-2.5M | [ ] |
| Kora Grid live | Yes | [ ] |

---

## Quick Reference: Key Contacts to Make

### Investors to Target
- [ ] Congruent Ventures
- [ ] Clean Energy Ventures
- [ ] Powerhouse Ventures
- [ ] Catalyst Fund
- [ ] Accion Venture Lab
- [ ] Omidyar Network
- [ ] Factor[e] Ventures
- [ ] Energy Access Ventures

### Customers to Target
- [ ] Africa GreenTec
- [ ] PowerGen
- [ ] Husk Power Systems
- [ ] Engie PowerCorner
- [ ] CrossBoundary Energy Access
- [ ] OMC Power
- [ ] Yoma Micro Power
- [ ] SunFunder portfolio companies

### Conferences to Attend
- [ ] AMDA Summit (Africa Mini-grid Developers Association)
- [ ] ARE Energy Access Forum
- [ ] Unlocking Solar Capital Africa
- [ ] GOGLA Global Off-Grid Solar Forum

### Grants to Apply For
- [ ] USAID Development Innovation Ventures (DIV)
- [ ] Shell Foundation
- [ ] GSMA Innovation Fund
- [ ] Rockefeller Foundation
- [ ] Good Energies Foundation

---

*Last updated: February 2025*
