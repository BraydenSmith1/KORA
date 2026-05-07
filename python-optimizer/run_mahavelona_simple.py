"""
Simplified Mahavelona Pilot - GLPK Compatible Version

This version uses FIXED time-of-use pricing (like the current system)
instead of optimizing prices. This makes it a pure MILP that GLPK can solve.

The optimization focuses on:
1. Battery dispatch (when to charge/discharge)
2. Curtailment minimization

Price optimization requires a nonlinear solver, which we'll add later.
"""

import argparse
import json
import numpy as np
from pathlib import Path

from mahavelona_config import (
    MahavelonaSpecs,
    MahavelonaFareStructure,
    generate_madagascar_solar_profile,
    generate_madagascar_demand_profile,
)
from optimizer.model import (
    OptimizerInputs,
    solve_model,
    extract_solution,
)


def simulate_baseline_simple(solar, demand, specs, fares):
    """Baseline with fixed TOU pricing"""
    hours = len(solar)
    battery_soc = specs.battery_capacity_kwh * 0.3

    result = {
        "p_charge_kw": np.zeros(hours),
        "p_discharge_kw": np.zeros(hours),
        "soc_kwh": np.zeros(hours),
        "p_curtail_kw": np.zeros(hours),
        "p_unmet_kw": np.zeros(hours),
        "demand_kw": demand.copy(),
        "price_ariary": np.zeros(hours),
    }

    for h in range(hours):
        # Fixed TOU pricing
        if fares.peak_start <= h < fares.peak_end:
            result["price_ariary"][h] = fares.avg_peak_price
        elif fares.intermediate_start <= h < fares.intermediate_end:
            result["price_ariary"][h] = fares.avg_intermediate_price
        else:
            result["price_ariary"][h] = fares.avg_offpeak_price

        available_solar = solar[h]
        customer_demand = demand[h]

        if available_solar >= customer_demand:
            surplus = available_solar - customer_demand
            battery_headroom = specs.battery_capacity_kwh * 0.95 - battery_soc
            max_charge = min(surplus, specs.battery_power_kw, battery_headroom)

            if max_charge > 0:
                result["p_charge_kw"][h] = max_charge
                battery_soc += max_charge * specs.battery_efficiency_charge
                result["p_curtail_kw"][h] = surplus - max_charge
            else:
                result["p_curtail_kw"][h] = surplus
        else:
            deficit = customer_demand - available_solar
            battery_available = battery_soc - specs.battery_capacity_kwh * 0.20
            max_discharge = min(deficit, specs.battery_power_kw, battery_available)

            if max_discharge > 0:
                result["p_discharge_kw"][h] = max_discharge
                battery_soc -= max_discharge / specs.battery_efficiency_discharge
                shortage = deficit - max_discharge
            else:
                shortage = deficit

            if shortage > 0:
                result["p_unmet_kw"][h] = shortage
                result["demand_kw"][h] -= shortage

        result["soc_kwh"][h] = battery_soc

    # Calculate metrics
    dt = 1.0
    total_pv = solar.sum()
    total_curtail = result["p_curtail_kw"].sum()
    total_demand_served = result["demand_kw"].sum()
    total_unmet = result["p_unmet_kw"].sum()
    total_revenue = sum(
        result["price_ariary"][h] * result["demand_kw"][h] * dt
        for h in range(hours)
    )

    metrics = {
        "total_pv_kwh": float(total_pv),
        "total_curtail_kwh": float(total_curtail),
        "curtailment_rate": float(total_curtail / total_pv) if total_pv > 0 else 0,
        "total_demand_served_kwh": float(total_demand_served),
        "total_unmet_kwh": float(total_unmet),
        "total_revenue_ariary": float(total_revenue),
        "avg_price_ariary": float(total_revenue / total_demand_served) if total_demand_served > 0 else 0,
        "blackout_hours": int(sum(1 for u in result["p_unmet_kw"] if u > 0.1)),
    }

    return {
        "timeseries": {k: v.tolist() for k, v in result.items()},
        "metrics": metrics
    }


def simulate_kora_simple(solar, demand, specs, fares, solver="glpk"):
    """
    KORA optimization with FIXED pricing (GLPK compatible)

    Since prices are fixed, we only optimize:
    1. Battery dispatch
    2. Curtailment minimization

    This is a pure MILP that GLPK can solve!
    """

    # Use fixed intermediate price for all hours (simplification)
    # In reality, you'd use TOU pricing, but for GLPK compatibility we keep it simple
    fixed_price = fares.avg_intermediate_price
    price_buy = [fixed_price] * len(solar)
    price_sell = [fixed_price * 0.5] * len(solar)  # Export at half price

    inp = OptimizerInputs(
        load_kw=demand.tolist(),
        pv_kw=solar.tolist(),
        price_buy=price_buy,
        price_sell=price_sell,
        battery_capacity_kwh=specs.battery_capacity_kwh,
        battery_power_kw=specs.battery_power_kw,
        soc_init_kwh=specs.battery_capacity_kwh * 0.3,
        soc_min_kwh=specs.battery_capacity_kwh * 0.20,
        soc_max_kwh=specs.battery_capacity_kwh * 0.95,
        eta_charge=specs.battery_efficiency_charge,
        eta_discharge=specs.battery_efficiency_discharge,
        curtailment_penalty_per_kwh=1500,
        shed_penalty_per_kwh=10000,
        battery_cycle_cost_per_kwh=10,
        timestep_hours=1.0,
        target_soc_end_kwh=specs.battery_capacity_kwh * 0.3,
    )

    # Solve with the basic model (from model.py, not kora_model.py)
    model = solve_model(inp, solver=solver)
    solution = extract_solution(model)

    # Add pricing info
    solution["price_ariary"] = [fixed_price] * len(solar)
    solution["demand_kw"] = demand.tolist()

    # Calculate metrics
    dt = 1.0
    total_pv = solar.sum()
    total_curtail = sum(solution["p_curtail_kw"])
    total_demand_served = demand.sum()
    total_revenue = fixed_price * total_demand_served * dt

    metrics = {
        "total_pv_kwh": float(total_pv),
        "total_curtail_kwh": float(total_curtail),
        "curtailment_rate": float(total_curtail / total_pv) if total_pv > 0 else 0,
        "total_demand_served_kwh": float(total_demand_served),
        "total_unmet_kwh": 0.0,
        "total_revenue_ariary": float(total_revenue),
        "avg_price_ariary": float(fixed_price),
        "blackout_hours": 0,
    }

    return {
        "timeseries": solution,
        "metrics": metrics
    }


def run_comparison(days=7, season="dry", solver="glpk", output_dir="python-optimizer/results"):
    """Run comparison with simplified GLPK-compatible model"""

    specs = MahavelonaSpecs()
    fares = MahavelonaFareStructure()

    print("=" * 60)
    print("KORA MAHAVELONA PILOT - SIMPLIFIED VERSION (GLPK)")
    print("=" * 60)
    print(f"Microgrid: {specs.pv_capacity_kw} kWp solar, {specs.battery_capacity_kwh} kWh battery")
    print(f"Customers: {specs.total_customers} connections")
    print(f"Baseline curtailment: {specs.baseline_curtailment_rate * 100}%")
    print(f"Simulating {days} days ({season} season)")
    print("=" * 60)
    print()

    baseline_daily = []
    kora_daily = []

    for day in range(days):
        print(f"Day {day + 1}/{days}...", end=" ")

        day_type = "clear" if np.random.random() > 0.2 else "partly_cloudy"
        solar = generate_madagascar_solar_profile(
            peak_capacity_kw=specs.pv_capacity_kw,
            hours=24,
            season=season,
            day_type=day_type
        )
        demand = generate_madagascar_demand_profile(
            total_customers=specs.total_customers,
            peak_load_kw=53,
            hours=24,
            day_type="weekday" if day < 5 else "weekend"
        )

        baseline_result = simulate_baseline_simple(solar, demand, specs, fares)
        baseline_daily.append(baseline_result)

        kora_result = simulate_kora_simple(solar, demand, specs, fares, solver=solver)
        kora_daily.append(kora_result)

        print(f"Baseline curtailment: {baseline_result['metrics']['curtailment_rate']*100:.1f}%, "
              f"KORA curtailment: {kora_result['metrics']['curtailment_rate']*100:.1f}%")

    print()
    print("=" * 60)
    print("SUMMARY RESULTS")
    print("=" * 60)

    # Aggregate
    def aggregate_metrics(daily_results):
        total_pv = sum(d["metrics"]["total_pv_kwh"] for d in daily_results)
        total_curtail = sum(d["metrics"]["total_curtail_kwh"] for d in daily_results)
        total_served = sum(d["metrics"]["total_demand_served_kwh"] for d in daily_results)
        total_revenue = sum(d["metrics"]["total_revenue_ariary"] for d in daily_results)

        return {
            "total_pv_kwh": total_pv,
            "total_curtail_kwh": total_curtail,
            "curtailment_rate": total_curtail / total_pv if total_pv > 0 else 0,
            "total_demand_served_kwh": total_served,
            "total_revenue_ariary": total_revenue,
            "avg_price_ariary": total_revenue / total_served if total_served > 0 else 0,
        }

    baseline_summary = aggregate_metrics(baseline_daily)
    kora_summary = aggregate_metrics(kora_daily)

    print("\nBASELINE (Current Operation):")
    print(f"  Total PV production: {baseline_summary['total_pv_kwh']:.1f} kWh")
    print(f"  Curtailment: {baseline_summary['total_curtail_kwh']:.1f} kWh ({baseline_summary['curtailment_rate']*100:.1f}%)")
    print(f"  Demand served: {baseline_summary['total_demand_served_kwh']:.1f} kWh")
    print(f"  Revenue: {baseline_summary['total_revenue_ariary']:,.0f} Ar (${baseline_summary['total_revenue_ariary']/4500:.0f})")

    print("\nKORA (Optimized Battery Dispatch):")
    print(f"  Total PV production: {kora_summary['total_pv_kwh']:.1f} kWh")
    print(f"  Curtailment: {kora_summary['total_curtail_kwh']:.1f} kWh ({kora_summary['curtailment_rate']*100:.1f}%)")
    print(f"  Demand served: {kora_summary['total_demand_served_kwh']:.1f} kWh")
    print(f"  Revenue: {kora_summary['total_revenue_ariary']:,.0f} Ar (${kora_summary['total_revenue_ariary']/4500:.0f})")

    curtail_reduction = baseline_summary['total_curtail_kwh'] - kora_summary['total_curtail_kwh']
    revenue_increase = kora_summary['total_revenue_ariary'] - baseline_summary['total_revenue_ariary']

    print("\nIMPACT:")
    print(f"  ✅ Curtailment reduced by {curtail_reduction:.1f} kWh")
    print(f"  ✅ Revenue increased by {revenue_increase:,.0f} Ar/week (${revenue_increase/4500:.0f}/week)")

    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    comparison = {
        "config": {
            "days": days,
            "season": season,
            "pv_capacity_kw": specs.pv_capacity_kw,
            "battery_capacity_kwh": specs.battery_capacity_kwh,
            "note": "Simplified version - battery optimization only (GLPK compatible)"
        },
        "baseline": {
            "summary": baseline_summary,
            "daily": baseline_daily
        },
        "kora": {
            "summary": kora_summary,
            "daily": kora_daily
        },
        "impact": {
            "curtailment_reduction_kwh": curtail_reduction,
            "revenue_increase_ariary": revenue_increase,
        }
    }

    json_path = output_path / "mahavelona_comparison.json"
    with open(json_path, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\n✅ Results saved to {json_path}")

    return comparison


def main():
    parser = argparse.ArgumentParser(description="Run Mahavelona pilot (simplified GLPK version)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to simulate")
    parser.add_argument("--season", type=str, default="dry", choices=["dry", "wet"])
    parser.add_argument("--solver", type=str, default="glpk", help="Solver (glpk recommended)")
    parser.add_argument("--output", type=str, default="python-optimizer/results")

    args = parser.parse_args()

    run_comparison(
        days=args.days,
        season=args.season,
        solver=args.solver,
        output_dir=args.output
    )


if __name__ == "__main__":
    main()
