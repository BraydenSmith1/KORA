#!/usr/bin/env python
"""
Test the basic linear optimizer (fixed prices) with GLPK.
This model is LINEAR so it works with GLPK.
"""

import numpy as np
from optimizer.model import OptimizerInputs, build_model, solve_model, extract_solution
from mahavelona_config import MahavelonaSpecs, generate_madagascar_solar_profile, generate_madagascar_demand_profile

print("=" * 70)
print("TESTING BASIC LINEAR OPTIMIZER WITH GLPK")
print("=" * 70)
print()

# Generate realistic data for Mahavelona
specs = MahavelonaSpecs()
hours = 24

solar = generate_madagascar_solar_profile(
    peak_capacity_kw=specs.pv_capacity_kw,
    hours=hours,
    season="dry",
    day_type="clear"
)

demand = generate_madagascar_demand_profile(
    total_customers=251,
    peak_load_kw=53,
    hours=hours
)

# Create optimizer inputs (LINEAR MODEL - fixed prices)
inputs = OptimizerInputs(
    load_kw=demand.tolist(),
    pv_kw=solar.tolist(),
    price_buy=[1750] * hours,  # Fixed price (Ariary/kWh)
    price_sell=[0] * hours,    # No feed-in (off-grid)
    battery_capacity_kwh=specs.battery_capacity_kwh,
    battery_power_kw=specs.battery_power_kw,
    soc_init_kwh=specs.battery_capacity_kwh * 0.5,  # Start at 50%
    soc_min_kwh=specs.battery_capacity_kwh * 0.2,
    soc_max_kwh=specs.battery_capacity_kwh * 0.95,
    eta_charge=0.94,
    eta_discharge=0.94,
    timestep_hours=1.0,
)

print(f"Microgrid: {specs.pv_capacity_kw} kWp solar, {specs.battery_capacity_kwh} kWh battery")
print(f"Simulating {hours} hours")
print()

# Build and solve
print("Building optimization model...")
model = build_model(inputs)

print("Solving with GLPK...")
print()

try:
    solved_model = solve_model(inputs, solver="glpk", time_limit_sec=60)

    print()
    print("=" * 70)
    print("✅ SUCCESS! Optimization completed")
    print("=" * 70)
    print()

    # Extract solution
    solution = extract_solution(solved_model)

    # Calculate metrics
    total_pv = sum(inputs.pv_kw)
    total_demand = sum(inputs.load_kw)
    total_curtailment = sum(solution["p_curtail_kw"])
    total_shed = sum(solution["p_shed_kw"])

    curtailment_rate = total_curtailment / total_pv * 100 if total_pv > 0 else 0

    print("RESULTS:")
    print(f"  Solar generation:    {total_pv:.1f} kWh")
    print(f"  Customer demand:     {total_demand:.1f} kWh")
    print(f"  Curtailment:         {total_curtailment:.1f} kWh ({curtailment_rate:.1f}%)")
    print(f"  Load shed:           {total_shed:.1f} kWh")
    print(f"  Final battery SOC:   {solution['soc_kwh'][-1]:.1f} kWh")
    print()

    # Show some hourly results
    print("Sample hours:")
    for h in [6, 10, 14, 18, 22]:
        print(f"  {h:02d}:00 - PV: {inputs.pv_kw[h]:5.1f} kW, "
              f"Demand: {inputs.load_kw[h]:5.1f} kW, "
              f"SOC: {solution['soc_kwh'][h]:5.1f} kWh, "
              f"Curtail: {solution['p_curtail_kw'][h]:5.1f} kW")
    print()
    print("=" * 70)
    print("✅ GLPK WORKS PERFECTLY WITH LINEAR MODEL!")
    print("=" * 70)
    print()
    print("Next step: We need to linearize the KORA model (dynamic pricing)")
    print("to work with GLPK, or install a nonlinear solver.")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
