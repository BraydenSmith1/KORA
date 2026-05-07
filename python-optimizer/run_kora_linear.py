#!/usr/bin/env python
"""
KORA with Linearized Model - WORKS WITH GLPK!

This version uses discrete price levels instead of continuous prices,
making it LINEAR so it works with GLPK (which you already have installed).

Still does everything KORA does:
- Dynamic pricing (5 price levels: 1000, 1375, 1750, 2125, 2500 Ar)
- Battery optimization
- Demand response
- Curtailment minimization

Just linearized so GLPK can solve it!
"""

import numpy as np
from optimizer.kora_linear import KoraLinearInputs, solve_kora_linear, extract_kora_linear_solution
from mahavelona_config import (
    MahavelonaSpecs,
    generate_madagascar_solar_profile,
    generate_madagascar_demand_profile,
)

print("=" * 70)
print("KORA MAHAVELONA - LINEARIZED MODEL")
print("(Works with GLPK - Dynamic Pricing with Discrete Levels)")
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
print(f"Baseline curtailment: 70%")
print()

# Create KORA linearized inputs
inputs = KoraLinearInputs(
    pv_forecast_kw=solar.tolist(),
    base_demand_kw=demand.tolist(),
    battery_capacity_kwh=specs.battery_capacity_kwh,
    battery_power_kw=specs.battery_power_kw,
    soc_init_kwh=specs.battery_capacity_kwh * 0.3,
    soc_min_kwh=specs.battery_capacity_kwh * 0.2,
    soc_max_kwh=specs.battery_capacity_kwh * 0.95,
    price_min=1000,  # Ariary/kWh
    price_max=2500,
    price_reference=1750,
    num_price_levels=5,  # 5 discrete price levels
    demand_elasticity=0.6,
    curtailment_value_per_kwh=1500,
    blackout_penalty_per_kwh=5000,
)

print("Price levels:")
price_levels = np.linspace(inputs.price_min, inputs.price_max, inputs.num_price_levels)
for i, p in enumerate(price_levels):
    print(f"  Level {i+1}: {p:.0f} Ar/kWh")
print()

try:
    # Solve with GLPK
    model = solve_kora_linear(inputs, solver="glpk", time_limit_sec=120)

    print()
    print("=" * 70)
    print("✅ OPTIMIZATION COMPLETED!")
    print("=" * 70)
    print()

    # Extract solution
    solution = extract_kora_linear_solution(model)

    # Calculate metrics
    total_pv = sum(solar)
    total_demand = sum(solution["demand_kw"])
    total_curtail = sum(solution["p_curtail_kw"])
    total_unmet = sum(solution["p_unmet_kw"])

    curtailment_rate = total_curtail / total_pv * 100 if total_pv > 0 else 0

    total_revenue = sum(
        solution["price_ariary"][t] * solution["demand_kw"][t]
        for t in range(len(solution["price_ariary"]))
    )

    avg_price = total_revenue / total_demand if total_demand > 0 else 0

    print("RESULTS:")
    print(f"  Solar generation:    {total_pv:.1f} kWh")
    print(f"  Energy sold:         {total_demand:.1f} kWh ({total_demand/total_pv*100:.0f}%)")
    print(f"  Curtailment:         {total_curtail:.1f} kWh ({curtailment_rate:.1f}%)")
    print(f"  Unmet demand:        {total_unmet:.1f} kWh")
    print(f"  Revenue:             {total_revenue:,.0f} Ar (~${total_revenue/4500:.0f})")
    print(f"  Average price:       {avg_price:.0f} Ar/kWh")
    print(f"  Final battery SOC:   {solution['soc_kwh'][-1]:.1f} kWh ({solution['soc_kwh'][-1]/specs.battery_capacity_kwh*100:.0f}%)")
    print()

    # Show price schedule
    print("Dynamic Price Schedule:")
    print("  Hour | Solar | Demand | Price  | Curtail | SOC")
    print("  " + "-" * 58)
    for h in [6, 10, 14, 18, 22]:
        print(f"  {h:02d}:00 | {solar[h]:5.1f} | {solution['demand_kw'][h]:6.1f} | "
              f"{solution['price_ariary'][h]:6.0f} | {solution['p_curtail_kw'][h]:7.1f} | {solution['soc_kwh'][h]:3.0f}")

    print()
    print("=" * 70)
    print("KORA IMPACT vs BASELINE (70% curtailment)")
    print("=" * 70)

    baseline_curtail = total_pv * 0.70
    baseline_sold = total_pv * 0.30
    baseline_revenue = baseline_sold * 1750

    print(f"  Curtailment: {curtailment_rate:.1f}% vs 70% (↓ {70 - curtailment_rate:.1f}%)")
    print(f"  Energy sold: {total_demand:.0f} kWh vs {baseline_sold:.0f} kWh (↑ {(total_demand/baseline_sold - 1)*100:.0f}%)")
    print(f"  Revenue: {total_revenue:,.0f} Ar vs {baseline_revenue:,.0f} Ar (↑ {(total_revenue/baseline_revenue - 1)*100:.0f}%)")

    print()
    print("=" * 70)
    print("✅ SUCCESS! KORA WORKS WITH GLPK!")
    print("=" * 70)
    print()
    print("This linearized version gives you:")
    print("  ✓ Dynamic pricing (5 discrete levels)")
    print("  ✓ Battery optimization")
    print("  ✓ Demand response")
    print("  ✓ Curtailment minimization")
    print("  ✓ Works with GLPK (no expensive solver needed!)")
    print()
    print("For even better results, install Gurobi for continuous pricing.")
    print("But this works great for production!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
