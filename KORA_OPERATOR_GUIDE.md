# KORA Operator Guide for Africa GreenTec
## Daily Operations Manual - Mahavelona Microgrid

**Role:** Grid Operator at Africa GreenTec, Mahavelona site
**Your Job:** Keep the lights on, manage the microgrid, maximize revenue

---

## Day 1: Monday Morning - First Week with KORA

### 7:00 AM - Starting Your Shift

**Step 1: Open the KORA Dashboard**

```
Browser: https://kora.mahavelona.africagreentec.com
Login: operator@agt.mg
Password: [your password]
```

**What you see:**

```
┌─────────────────────────────────────────────────────────────────┐
│  KORA Optimizer - Mahavelona                    🟢 Connected    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current Status (07:04)                                         │
│  ├─ Solar Production:     15.2 kW                               │
│  ├─ Customer Demand:      12.8 kW                               │
│  ├─ Battery SOC:          67% (77 kWh)                          │
│  ├─ Current Price:        1,650 Ar/kWh                          │
│  └─ Curtailment:          0 kW                                  │
│                                                                  │
│  Today's Forecast                                               │
│  ├─ KORA Status:          ✓ Running (Auto Mode)                │
│  ├─ Last Run:             06:45 AM (19 min ago)                │
│  ├─ Next Run:             07:00 AM (in 1 min)                  │
│  ├─ Solve Time:           8.2 seconds                           │
│  └─ Projected Revenue:    892,000 Ar                            │
│                                                                  │
│  🎯 KPIs (Last 24h)                                             │
│  ├─ Energy Sold:          487 kWh                               │
│  ├─ Curtailment:          12% (down from 70% baseline!)         │
│  ├─ Revenue:              854,000 Ar                            │
│  └─ Uptime:               100%                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Step 2: Check Alerts Panel**

```
┌─────────────────────────────────────────────────────────────────┐
│  🔔 Alerts (0 active)                                           │
├─────────────────────────────────────────────────────────────────┤
│  ✓ All systems normal                                           │
│                                                                  │
│  Recent (last 7 days):                                          │
│  └─ 02/15 14:23 - High curtailment warning (23%) - Acknowledged │
└─────────────────────────────────────────────────────────────────┘
```

**Your Action:** Everything looks good. KORA is running in auto mode, no alerts. You can focus on other tasks.

---

### 9:30 AM - Mid-Morning Check

**What Changed:**

```
Current Status (09:32)
├─ Solar Production:     95.3 kW  ⬆️
├─ Customer Demand:      38.4 kW  ⬆️
├─ Battery SOC:          82% (94 kWh)  ⬆️
├─ Current Price:        1,100 Ar/kWh  ⬇️ (Discount!)
└─ Curtailment:          3 kW

Price Schedule (next 6 hours):
09:00-10:00    1,100 Ar/kWh  ⬇️ Low (stimulate demand)
10:00-11:00    1,050 Ar/kWh  ⬇️ Lowest (peak solar)
11:00-12:00    1,150 Ar/kWh  ⬇️ Low
12:00-13:00    1,300 Ar/kWh  → Normal
13:00-14:00    1,450 Ar/kWh  → Normal
14:00-15:00    1,600 Ar/kWh  → Normal
```

**What KORA Did:**
- Detected high solar production (95 kW)
- Dropped price to 1,100 Ar (37% off!)
- Customers responded: demand increased from ~26 kW to 38 kW
- Battery is charging at 54 kW (max rate)
- Only 3 kW curtailment (instead of 60+ kW baseline)

**Your Action:** None needed. This is working as designed.

**Optional:** Post on community board: "⚡ Low electricity prices today 9am-2pm! Great time to run heavy equipment, do laundry, charge batteries!"

---

### 12:00 PM - Lunch Break

**Quick Check from Phone:**

Mobile dashboard shows:
```
Mahavelona 🟢
SOC: 91% | Price: 1,150 Ar | Curtail: 1 kW
All normal ✓
```

**Your Action:** Enjoy lunch. System is stable.

---

### 3:00 PM - Afternoon Check

**What you see:**

```
Current Status (15:04)
├─ Solar Production:     72.1 kW  ⬇️ (sun angle decreasing)
├─ Customer Demand:      28.9 kW
├─ Battery SOC:          93% (107 kWh)  Near full
├─ Current Price:        1,600 Ar/kWh  → Normal
└─ Curtailment:          8 kW
```

**What KORA Did:**
- Battery is 93% full (near max of 95%)
- Still some solar curtailment (8 kW)
- Price returning to normal as we prepare for evening peak

**Your Action:** None. This is expected behavior.

---

### 6:30 PM - Evening Peak Approaching

**Critical Time - This is where KORA shines**

```
Current Status (18:34)
├─ Solar Production:     12.4 kW  ⬇️ (sunset)
├─ Customer Demand:      44.2 kW  ⬆️ (cooking, lighting)
├─ Battery SOC:          78% (90 kWh)  ⬇️ Discharging
├─ Current Price:        2,200 Ar/kWh  ⬆️ (Peak pricing)
└─ Curtailment:          0 kW

Battery Discharge:       32 kW
Grid Import:             0 kW (off-grid)
Unmet Demand:            0 kW ✓ (No blackout!)
```

**What KORA Did:**
- Raised price to 2,200 Ar to reduce demand slightly
- Battery discharging at 32 kW (sustainable rate)
- Solar (12 kW) + Battery (32 kW) = 44 kW supply
- Demand naturally reduced from ~50 kW to 44 kW due to price signal
- **Zero blackouts**

**Comparison to Baseline (without KORA):**
- Battery would be at 45% SOC (depleted earlier)
- Demand would be 50 kW
- Supply shortage: 6 kW → BLACKOUT for ~150 customers
- Operator would manually shed loads (public lighting first)

**Your Action:** Monitor but don't intervene. KORA is managing the peak perfectly.

---

### 9:00 PM - Evening Wind-Down

```
Current Status (21:07)
├─ Solar Production:     0 kW  (Night)
├─ Customer Demand:      22.4 kW  ⬇️ (people going to bed)
├─ Battery SOC:          52% (60 kWh)
├─ Current Price:        1,900 Ar/kWh  ⬆️ (Preserve battery)
└─ Grid Import:          0 kW
```

**What KORA Did:**
- Maintained higher prices through evening to extend battery life
- Battery lasted through entire peak period
- Now at 52% SOC with 60 kWh remaining (enough for overnight)
- Will discharge slowly overnight, reach ~35% by sunrise

**Your Action:** Review daily summary before end of shift.

---

### End of Shift - Daily Report

**Click "Export Daily Report" button**

```
=== Mahavelona Daily Report - 2026-02-17 ===

ENERGY BALANCE:
Solar Generation:        542 kWh
Energy Sold:             489 kWh (90%)
Curtailment:             53 kWh (10%)
Battery Cycles:          0.7 (gentle cycling)

FINANCIAL:
Revenue:                 872,450 Ar ($194.25)
Avg Price:              1,784 Ar/kWh
Price Range:            1,050 - 2,200 Ar/kWh

RELIABILITY:
Uptime:                  100%
Blackout Events:         0
Unmet Demand:            0 kWh

KORA PERFORMANCE:
Optimization Runs:       96 (every 15 min)
Avg Solve Time:          7.8 seconds
Failed Runs:             0
Cache Hit Rate:          12%

COMPARISON TO BASELINE:
Energy Sold:             +197% (165 → 489 kWh)
Curtailment:             -86% (383 → 53 kWh)
Revenue:                 +203% ($64 → $194)

Status: ✓ EXCELLENT DAY
```

**Your Action:**
1. Save report to shared drive
2. If unusual patterns, add notes
3. Sign off to night operator

---

## Day 7: Things Get Interesting - Cloudy Day

### 8:00 AM - Weather Alert

**What you see:**

```
🌧️ Weather Alert
Forecast: Partly cloudy, possible rain
Expected PV: 40% of normal (220 kWh vs 548 kWh)

KORA Adjustment:
├─ Switched to "conservative mode"
├─ Price floor raised: 1,400 Ar (vs 1,050 Ar)
├─ Battery reserve: Keeping >50% SOC for evening
└─ Priority loads: Hospital, water pump protected
```

**What KORA Did:**
- Detected low solar forecast from weather API
- Automatically adjusted strategy:
  - Higher prices throughout day (preserve battery)
  - Less aggressive demand stimulation
  - Protect critical loads

**Your Action:**
1. Check weather forecast yourself (confirm)
2. Notify customers: "Limited solar today - please defer non-essential loads"
3. Monitor more frequently (every hour instead of every 3 hours)

---

### 10:00 AM - Lower Solar Than Expected

```
Current Status (10:12)
├─ Solar Production:     32.1 kW  ⬇️⬇️ (Only 30% of normal!)
├─ Customer Demand:      26.4 kW  (Price: 1,650 Ar - higher than usual)
├─ Battery SOC:          71% (82 kWh)
├─ Curtailment:          0 kW
└─ Net Battery:          +6 kW (Charging slowly)

🟡 Advisory:
Solar production below forecast. KORA compensating with price increases.
Battery expected to last until 22:00 (vs 24:00 on normal day).
```

**What KORA Did:**
- Raised prices to 1,650 Ar (would normally be 1,100 Ar)
- Reduced demand from ~38 kW to 26 kW
- Still charging battery (slowly)
- Planning for limited evening coverage

**Your Action:**
1. Review evening forecast demand
2. Prepare load shedding plan (just in case):
   - Priority 1: Hospital, water pump, telecom (never shed)
   - Priority 2: Households, schools
   - Priority 3: SMEs, public lighting
3. Send SMS to commercial customers: "Limited power today - critical loads only after 8pm"

---

### 6:00 PM - Managing the Evening Carefully

```
Current Status (18:15)
├─ Solar Production:     3.2 kW  (Sunset)
├─ Customer Demand:      36.8 kW  ⬇️ (Normally 50+ kW)
├─ Battery SOC:          63% (72 kWh)
├─ Current Price:        2,400 Ar/kWh  ⬆️⬆️ (Near max!)
└─ Battery Discharge:    34 kW

🟡 Warning:
High prices active. Battery will deplete by 21:30 at current rate.
Load shedding may be required after 21:30.
```

**What KORA Did:**
- Pushed price to near maximum (2,400 Ar vs 2,500 Ar cap)
- Customers responded: demand dropped from typical 50 kW to 37 kW
- Extended battery life by 2.5 hours
- Gave you time to prepare

**Your Action:**
1. **Manual Override Consideration:**
   - Option A: Let KORA continue (may have brief outage after 21:30)
   - Option B: Manually shed Priority 3 loads now (public lighting)

2. **Your Decision:** Option B - proactive load shedding

3. **Action in Dashboard:**
   ```
   Click "Manual Override"
   ├─ Load Shedding: Priority 3 (Public Lighting, 8 kW)
   ├─ Duration: Until 23:00
   └─ Reason: "Cloudy day - preserving battery for critical loads"

   KORA Adjustment:
   └─ Reoptimizing with 8 kW less demand...
   └─ New projection: Battery lasts until 23:45 ✓
   ```

**Customer Communication:**
- SMS sent automatically: "Due to low solar today, public lighting reduced 6pm-11pm. Home power unaffected. Thank you for understanding."

---

### 10:00 PM - Crisis Averted

```
Current Status (22:04)
├─ Solar Production:     0 kW
├─ Customer Demand:      18.2 kW  (8 kW shed from public lighting)
├─ Battery SOC:          38% (44 kWh)  ✓ Safe zone
├─ Current Price:        2,200 Ar/kWh
└─ Battery Discharge:    18 kW

✓ Success:
Load shedding + high prices extended battery through evening peak.
Battery will last until 06:00 (sunrise).
No household blackouts. Critical loads protected.
```

**Your Action:**
1. Log incident in operations journal
2. Restore public lighting at 23:00 as planned
3. Report to management: "Managed cloudy day successfully - 0 critical blackouts"

---

## Week 2: Equipment Failure Scenario

### 2:00 PM Tuesday - Battery Fault

**SCADA Alarm:**
```
🔴 CRITICAL ALERT
Battery Module 3 offline
Available capacity: 85 kWh (was 115 kWh)
Available power: 40 kW (was 54 kW)
```

**What You Do:**

**Step 1: Update KORA Configuration**
```
Dashboard → Settings → Site Configuration

Battery Settings:
├─ Capacity: 85 kWh  (was 115 kWh) ✏️
├─ Power: 40 kW  (was 54 kW) ✏️
└─ Status: ⚠️ DEGRADED MODE

Click "Apply & Reoptimize"
```

**Step 2: KORA Response (Automatic)**
```
⚠️ Configuration Updated

KORA Adjustments:
├─ Reduced charging power limit: 54 → 40 kW
├─ Reduced SOC range: 95 kWh → 70 kWh usable
├─ Increased price floor: 1,050 → 1,300 Ar (conserve energy)
├─ Earlier evening peak management (start at 17:00 vs 18:00)

Reoptimizing schedule... ✓ Done

Impact:
├─ Curtailment: 10% → 18% (less storage capacity)
├─ Revenue: -12% (less energy to sell in evening)
├─ Reliability: MAINTAINED (battery still sufficient)
```

**Step 3: Customer Communication**
```
SMS Template (auto-sent):
"Important: Battery maintenance in progress. Power available but
limited evening hours. Avoid heavy loads 6-10pm. Updates at
kora.mahavelona.com"
```

**Step 4: Your Report to Maintenance**
```
Email to: maintenance@africagreentec.com
Subject: Battery Module 3 Failure - Mahavelona

Status: Site operational with reduced capacity
KORA: Adjusted to degraded mode automatically
Impact: -12% revenue until repair
Priority: HIGH (need replacement within 1 week)
Site: Stable for now
```

**KORA ran 24/7 for 4 days with degraded battery until replacement arrived. Zero blackouts.**

---

## Week 3: You're Now an Expert

### Monday Morning - Proactive Optimization

**What You Do Now (Advanced):**

**9:00 AM - Review Weekly Trends**
```
Dashboard → Analytics → Weekly View

Patterns Detected:
├─ Thursdays: 15% higher demand (market day!)
├─ Sundays: 20% lower demand (church day)
├─ Mornings: Demand spike at 07:00 (phone charging)
└─ Weather: Rainy season starting (Feb-Mar)

Your Action:
├─ Adjust demand forecasts for market day
├─ Schedule battery maintenance on Sundays (low demand)
└─ Review curtailment patterns
```

**10:00 AM - Optimization Review**
```
Dashboard → Runs → Recent

Last 24 hours: 96 runs
├─ Success rate: 100%
├─ Avg solve time: 7.2 sec
├─ Cache hits: 18% (repeated weather patterns)
└─ Manual overrides: 1 (your load shedding on cloudy day)

Click on any run to see details:
├─ Input data (PV forecast, demand forecast)
├─ Solver output (price schedule, battery plan)
├─ Actual vs forecast (how accurate was it?)
└─ Revenue impact
```

**11:00 AM - Fine-Tuning**
```
Settings → Optimization Parameters

Adjustments you can make:
├─ Price bounds (1,000-2,500 Ar) - keep as is
├─ Demand elasticity (0.6) - increase to 0.7? Test it.
├─ Curtailment penalty (1,500 Ar) - keep as is
├─ Battery SOC limits (20-95%) - keep as is

Test Mode:
├─ Run "what-if" scenarios
├─ Compare results before applying
└─ Validate with supervisor before changing
```

---

## Month 2: Advanced Operations

### Task 1: Compare Performance

**Generate Monthly Report**
```
Dashboard → Reports → Monthly Summary

February 2026 vs February 2025 (Baseline):

Energy:
├─ Generation: 15,340 kWh (same PV capacity)
├─ Sold: 13,720 kWh (vs 4,620 kWh baseline) +197%
├─ Curtailment: 1,620 kWh (11% vs 70%) -84%

Financial:
├─ Revenue: $4,285 (vs $1,440 baseline) +197%
├─ ARPU: $17.07/customer (vs $5.74) +197%
├─ Avg Price: 1,788 Ar/kWh (vs 1,750 Ar) +2%

Reliability:
├─ Uptime: 99.8% (vs 94.3% baseline) +5.5%
├─ Blackout hours: 4.2 hrs (vs 168 hrs) -97%
├─ Customer complaints: 3 (vs 47) -94%

KORA Stats:
├─ Total runs: 2,688
├─ Success rate: 99.9%
├─ Avg solve time: 7.4 sec
├─ Failures: 2 (both solver timeouts, used fallback)
```

**Your Monthly Report to Management:**
```
To: regional@africagreentec.com
Subject: Mahavelona Monthly Performance - Feb 2026

Highlights:
✓ Revenue up 197% month-over-month
✓ Curtailment reduced from 70% to 11%
✓ Zero critical blackouts
✓ Customer satisfaction improved (94% fewer complaints)
✓ KORA system reliability: 99.9%

Challenges:
- 1 cloudy day required manual load shedding
- Battery Module 3 failure (4 days degraded operation)

Recommendations:
- Continue KORA deployment
- Add 2nd battery module for redundancy
- Train backup operator on KORA dashboard

[Detailed charts and data attached]
```

---

## Common Tasks - Quick Reference

### Task: Manual Price Override

**When:** Special event (wedding, festival, emergency)

```
Dashboard → Manual Override → Price Schedule

Example: Village festival today
├─ Override period: 14:00 - 22:00
├─ Fixed price: 1,500 Ar/kWh (discount for community)
├─ Reason: "Festival pricing"
├─ Duration: 8 hours

KORA Response:
└─ Will honor your override
└─ Optimize battery/curtailment around fixed price
└─ Resume auto-pricing after 22:00
```

---

### Task: Emergency Shutdown

**When:** Severe storm, equipment danger

```
Dashboard → Emergency → Shutdown Sequence

Options:
A) Graceful shutdown (KORA ramps down over 15 min)
B) Immediate shutdown (cut all loads now)

Your choice: A (Graceful)

KORA Actions:
├─ 14:45: Raise prices to reduce demand
├─ 14:50: Shed Priority 3 loads
├─ 14:55: Shed Priority 2 loads
├─ 15:00: Only Priority 1 loads remain
├─ 15:00: Safe to disconnect battery/solar

└─ All load changes logged
└─ Customers notified via SMS
```

---

### Task: Viewing Real-Time Data

**When:** Troubleshooting, monitoring

```
Dashboard → Live Telemetry

Modbus Data (updates every 1 second):
├─ PV Voltage: 385 V
├─ PV Current: 248 A
├─ PV Power: 95.4 kW
├─ Battery Voltage: 51.2 V
├─ Battery Current: -42 A (charging)
├─ Battery SOC: 82.3%
├─ Battery Temp: 28°C ✓
├─ Inverter Freq: 50.0 Hz ✓
├─ Grid Voltage: 230 V ✓
└─ Load Power: 38.2 kW

Alarms:
└─ None

Health:
├─ KORA Service: 🟢 Running
├─ Modbus: 🟢 Connected
├─ Database: 🟢 Healthy
└─ API: 🟢 Online
```

---

## Troubleshooting Guide

### Problem: KORA Shows "Solver Timeout"

**Symptoms:**
```
🟡 Warning
Last optimization run failed: Solver timeout (60 sec)
Fallback: Using previous price schedule
```

**What It Means:**
- Optimization problem was too complex to solve in 60 seconds
- Usually happens with extreme weather or equipment failures

**What KORA Did:**
- Used the price schedule from 15 minutes ago
- Logged the error
- Will retry next run (15 minutes)

**Your Action:**
1. Check if multiple runs failing (rare) or one-off (normal)
2. If repeated failures:
   - Settings → Optimization → Time Limit: 60 sec → 120 sec
   - Or contact support

---

### Problem: "High Curtailment" Alert

**Symptoms:**
```
⚠️ Alert
Curtailment rate: 28% (threshold: 20%)
Last 4 hours average
```

**Possible Causes:**
1. **Very sunny day** - More solar than battery can absorb
   - Action: None, this happens occasionally

2. **Low demand** - Customers not responding to price signals
   - Action: Check if it's a holiday, Sunday, special event
   - Action: Review demand elasticity setting

3. **Battery full early** - Need more storage capacity
   - Action: Report to management (capacity expansion needed)

**Your Action:**
```
Dashboard → Alerts → Acknowledge
Add note: "Very sunny day, demand lower than forecast (Sunday)"
```

---

### Problem: Prices Seem Too High

**Symptoms:**
Customer complaint: "Why is electricity 2,400 Ar/kWh? That's expensive!"

**Your Response:**
1. **Check context:**
   ```
   Dashboard → Price History → Show customer context

   Today's prices:
   ├─ 09:00-14:00: 1,100-1,300 Ar (CHEAP!)
   ├─ 14:00-18:00: 1,600-1,800 Ar (Normal)
   └─ 18:00-21:00: 2,200-2,400 Ar (High)

   Customer's daily average: 1,620 Ar/kWh
   Baseline average: 1,750 Ar/kWh

   Savings: 7.4% vs baseline!
   ```

2. **Explain to customer:**
   - "High prices 6-9pm encourage shifting loads to midday when solar is abundant"
   - "Your average price is LOWER than before (1,620 vs 1,750 Ar)"
   - "If you run laundry at 11am tomorrow, you'll pay 1,100 Ar - 37% off!"

3. **Educational materials:**
   - Share: "How dynamic pricing saves you money" pamphlet
   - Show their monthly bill: Total savings highlighted

---

## Your Success Metrics (Monthly Review)

Management evaluates you on:

| Metric | Target | Your Feb Performance |
|--------|--------|---------------------|
| **Uptime** | >98% | 99.8% ✓ |
| **Revenue** | >$3,500/mo | $4,285 ✓ |
| **Curtailment** | <15% | 11% ✓ |
| **Blackouts** | <10 hrs/mo | 4.2 hrs ✓ |
| **Customer Complaints** | <10/mo | 3 ✓ |
| **KORA Reliability** | >99% | 99.9% ✓ |

**Result: Excellent Performance. You get a bonus!**

---

## What You Tell Your Friends

*"Before KORA, my job was stressful. Battery would fill by 10am, we'd waste 70% of solar. Evenings were constant blackouts, angry customers, manual load shedding.*

*Now? KORA handles it. Prices adjust automatically. Battery lasts through the evening. Curtailment is down to 10%. Revenue tripled. I actually have time to do preventive maintenance instead of firefighting.*

*I just monitor the dashboard, handle the rare edge cases, and go home knowing the lights will stay on.*

*Best upgrade we've ever made."*

---

## The Bottom Line

**As an AGT Operator, KORA:**
- ✅ Reduces your stress (no more manual pricing decisions)
- ✅ Increases your success (better performance metrics)
- ✅ Frees your time (automation handles 99% of situations)
- ✅ Makes customers happier (fewer blackouts, lower average prices)
- ✅ Makes your boss happy (3× revenue increase)

**You stay in control** with manual override, but 99% of the time, you're just monitoring.

Welcome to stress-free microgrid operations.
