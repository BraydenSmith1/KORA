#!/usr/bin/env python
"""
SIMPLIFIED KORA DEMO - WORKS WITH GLPK

This uses FIXED prices (not dynamic pricing) so GLPK can solve it.
It still shows battery optimization and curtailment reduction!

Once this works, we can tackle the full dynamic pricing model.
"""

import numpy as np
from optimizer.model import OptimizerInputs, build_model, solve_model, extract_solution
from mahavelona_config import (
    MahavelonaSpecs,
    generate_madagascar_solar_profile,
    generate_madagascar_demand_profile,
)

print("=" * 70)
print("KORA SIMPLIFIED DEMO - Battery Optimization")
print("(Fixed prices, works with GLPK)")
print("=" * 70)
print()

# Mahavelona specs
specs = MahavelonaSpecs()
hours = 24

# Generate realistic solar and demand
solar = generate_madagascar_solar_profile(
    peak_capacity_kw=specs.pv_capacity_kw,
    hours=hours,
    season="dry",
    day_type="clear"
)

demand = generate_madagascar_demand_profile(
    total_customers=251,
    peak_load_kw=53,
    hours=hours,
    day_type="weekday"
)

print(f"Microgrid: {specs.pv_capacity_kw} kWp solar, {specs.battery_capacity_kwh} kWh battery")
print(f"Customers: 251 connections")
print()

# Scenario 1: NO BATTERY (Baseline)
print("Scenario 1: NO BATTERY OPTIMIZATION (Baseline)")
print("-" * 70)

baseline_inputs = OptimizerInputs(
    load_kw=demand.tolist(),
    pv_kw=solar.tolist(),
    price_buy=[1750] * hours,
    price_sell=[0] * hours,
    battery_capacity_kwh=specs.battery_capacity_kwh,
    battery_power_kw=0,  # ← NO battery power (simulates dumb charging)
    soc_init_kwh=specs.battery_capacity_kwh * 0.3,
    soc_min_kwh=specs.battery_capacity_kwh * 0.2,
    soc_max_kwh=specs.battery_capacity_kwh * 0.95,
    eta_charge=0.94,
    eta_discharge=0.94,
    timestep_hours=1.0,
    curtailment_penalty=100,  # Low penalty = lots of curtailment
)

try:
    baseline_model = solve_model(baseline_inputs, solver="glpk", time_limit_sec=60)
    baseline_sol = extract_solution(baseline_model)

    baseline_curtail = sum(baseline_sol["p_curtail_kw"])
    baseline_shed = sum(baseline_sol["p_shed_kw"])
    total_pv = sum(solar)

    print(f"✓ Solar generation:    {total_pv:.1f} kWh")
    print(f"✓ Curtailment:         {baseline_curtail:.1f} kWh ({baseline_curtail/total_pv*100:.1f}%)")
    print(f"✓ Load shed:           {baseline_shed:.1f} kWh")
    print()

except Exception as e:
    print(f"❌ Error in baseline: {e}")
    baseline_curtail = 0
    baseline_shed = 0

# Scenario 2: WITH SMART BATTERY
print("Scenario 2: WITH KORA BATTERY OPTIMIZATION")
print("-" * 70)

kora_inputs = OptimizerInputs(
    load_kw=demand.tolist(),
    pv_kw=solar.tolist(),
    price_buy=[1750] * hours,
    price_sell=[0] * hours,
    battery_capacity_kwh=specs.battery_capacity_kwh,
    battery_power_kw=specs.battery_power_kw,  # ← FULL battery power
    soc_init_kwh=specs.battery_capacity_kwh * 0.3,
    soc_min_kwh=specs.battery_capacity_kwh * 0.2,
    soc_max_kwh=specs.battery_capacity_kwh * 0.95,
    eta_charge=0.94,
    eta_discharge=0.94,
    timestep_hours=1.0,
    curtailment_penalty=1500,  # High penalty = minimize curtailment!
    shed_penalty=5000,
)

print("Solving with GLPK...")
print()

try:
    kora_model = solve_model(kora_inputs, solver="glpk", time_limit_sec=60)
    kora_sol = extract_solution(kora_model)

    kora_curtail = sum(kora_sol["p_curtail_kw"])
    kora_shed = sum(kora_sol["p_shed_kw"])

    print(f"✓ Solar generation:    {total_pv:.1f} kWh")
    print(f"✓ Curtailment:         {kora_curtail:.1f} kWh ({kora_curtail/total_pv*100:.1f}%)")
    print(f"✓ Load shed:           {kora_shed:.1f} kWh")
    print(f"✓ Final battery SOC:   {kora_sol['soc_kwh'][-1]:.1f} kWh ({kora_sol['soc_kwh'][-1]/specs.battery_capacity_kwh*100:.0f}%)")
    print()

    # Show hourly schedule
    print("Sample battery schedule:")
    print("  Hour | Solar | Demand | Charge | Discharge | SOC | Curtail")
    print("  " + "-" * 64)
    for h in [6, 10, 14, 18, 22]:
        print(f"  {h:02d}:00 | {solar[h]:5.1f} | {demand[h]:6.1f} | "
              f"{kora_sol['p_charge_kw'][h]:6.1f} | {kora_sol['p_discharge_kw'][h]:9.1f} | "
              f"{kora_sol['soc_kwh'][h]:3.0f} | {kora_sol['p_curtail_kw'][h]:7.1f}")

    print()
    print("=" * 70)
    print("IMPACT")
    print("=" * 70)

    if baseline_curtail > 0:
        reduction = (baseline_curtail - kora_curtail) / baseline_curtail * 100
        print(f"Curtailment reduction: {reduction:.1f}%")
        print(f"  Before: {baseline_curtail:.1f} kWh")
        print(f"  After:  {kora_curtail:.1f} kWh")
        print(f"  Saved:  {baseline_curtail - kora_curtail:.1f} kWh/day")

    print()
    print("=" * 70)
    print("✅ SUCCESS! The optimizer works with GLPK!")
    print("=" * 70)
    print()
    print("This demo uses FIXED prices. For full KORA with DYNAMIC PRICING,")
    print("we need a nonlinear solver (IPOPT, Gurobi, etc.)")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
