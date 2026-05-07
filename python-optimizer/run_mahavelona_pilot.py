"""
Mahavelona Pilot Simulation Runner

This script runs a side-by-side comparison:
- BASELINE: Current operation (70% curtailment, fixed prices)
- KORA: Optimized operation (dynamic pricing, curtailment minimization)

Outputs:
- Console summary
- CSV files for visualization
- JSON results for web dashboard
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np

from mahavelona_config import (
    MahavelonaSpecs,
    MahavelonaFareStructure,
    generate_madagascar_solar_profile,
    generate_madagascar_demand_profile,
    generate_baseline_scenario,
)
from optimizer.kora_model import (
    KoraOptimizerInputs,
    solve_kora_model,
    extract_kora_solution,
    calculate_metrics,
)


def simulate_baseline(
    solar_kw: np.ndarray,
    demand_kw: np.ndarray,
    specs: MahavelonaSpecs,
    fares: MahavelonaFareStructure
) -> Dict:
    """
    Simulate CURRENT operation (what Africa GreenTec is doing now).

    Rules:
    1. Charge battery whenever solar > demand (until full)
    2. Battery full by 10am → all afternoon solar curtailed
    3. Evening: discharge battery to meet peak
    4. Fixed time-of-use pricing
    """

    hours = len(solar_kw)
    battery_soc = specs.battery_capacity_kwh * 0.3  # Start at 30%

    # Initialize result arrays
    result = {
        "p_charge_kw": np.zeros(hours),
        "p_discharge_kw": np.zeros(hours),
        "soc_kwh": np.zeros(hours),
        "p_curtail_kw": np.zeros(hours),
        "p_unmet_kw": np.zeros(hours),
        "demand_kw": demand_kw.copy(),  # No demand response in baseline
        "price_ariary": np.zeros(hours),
    }

    for h in range(hours):
        # Determine price (fixed time-of-use)
        if fares.peak_start <= h < fares.peak_end:  # 5pm-11pm
            result["price_ariary"][h] = fares.avg_peak_price
        elif fares.intermediate_start <= h < fares.intermediate_end:  # 8am-5pm
            result["price_ariary"][h] = fares.avg_intermediate_price
        else:  # Off-peak
            result["price_ariary"][h] = fares.avg_offpeak_price

        available_solar = solar_kw[h]
        customer_demand = demand_kw[h]

        if available_solar >= customer_demand:
            # Surplus solar
            surplus = available_solar - customer_demand

            # Try to charge battery
            battery_headroom = specs.battery_capacity_kwh * 0.95 - battery_soc
            max_charge = min(
                surplus,
                specs.battery_power_kw,
                battery_headroom
            )

            if max_charge > 0:
                result["p_charge_kw"][h] = max_charge
                battery_soc += max_charge * specs.battery_efficiency_charge
                result["p_curtail_kw"][h] = surplus - max_charge
            else:
                # Battery full → curtail all surplus
                result["p_curtail_kw"][h] = surplus

        else:
            # Deficit → discharge battery
            deficit = customer_demand - available_solar
            battery_available = battery_soc - specs.battery_capacity_kwh * 0.20  # Don't go below 20%

            max_discharge = min(
                deficit,
                specs.battery_power_kw,
                battery_available
            )

            if max_discharge > 0:
                result["p_discharge_kw"][h] = max_discharge
                battery_soc -= max_discharge / specs.battery_efficiency_discharge
                shortage = deficit - max_discharge
            else:
                shortage = deficit

            if shortage > 0:
                # Load shedding (blackout!)
                result["p_unmet_kw"][h] = shortage
                result["demand_kw"][h] -= shortage  # Actual demand served

        result["soc_kwh"][h] = battery_soc

    # Calculate metrics
    dt = 1.0  # 1-hour timesteps
    total_pv = solar_kw.sum()
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


def simulate_kora(
    solar_kw: np.ndarray,
    base_demand_kw: np.ndarray,
    specs: MahavelonaSpecs,
    fares: MahavelonaFareStructure,
    solver: str = "highs"
) -> Dict:
    """
    Simulate KORA optimized operation.

    The optimizer will:
    1. Find optimal hourly prices to minimize curtailment
    2. Predict customer demand response to those prices
    3. Schedule battery to maximize utilization
    """

    # Build optimizer inputs
    inp = KoraOptimizerInputs(
        pv_forecast_kw=solar_kw.tolist(),
        base_demand_kw=base_demand_kw.tolist(),
        battery_capacity_kwh=specs.battery_capacity_kwh,
        battery_power_kw=specs.battery_power_kw,
        soc_init_kwh=specs.battery_capacity_kwh * 0.3,  # Start at 30%
        soc_min_kwh=specs.battery_capacity_kwh * 0.20,
        soc_max_kwh=specs.battery_capacity_kwh * 0.95,
        eta_charge=specs.battery_efficiency_charge,
        eta_discharge=specs.battery_efficiency_discharge,
        battery_cycle_cost_per_kwh=10,  # Ariary/kWh (degradation cost)
        price_min=1000,   # Min affordable price (Ariary/kWh)
        price_max=2500,   # Max regulatory price (Ariary/kWh)
        price_reference=fares.avg_intermediate_price,  # Reference (baseline avg)
        demand_elasticity=0.6,  # Conservative estimate (customers moderately responsive)
        curtailment_value_per_kwh=1500,  # Lost revenue opportunity
        blackout_penalty_per_kwh=10000,  # VERY high (blackouts are terrible!)
        timestep_hours=1.0,
        target_soc_end_kwh=specs.battery_capacity_kwh * 0.3,  # End where we started
    )

    # Solve optimization
    # Try highs first, fall back to glpk if highs not available
    try:
        model = solve_kora_model(inp, solver=solver, time_limit_sec=120)
    except Exception as e:
        print(f"Failed with {solver}, trying glpk...")
        model = solve_kora_model(inp, solver='glpk', time_limit_sec=120)
    solution = extract_kora_solution(model)
    metrics = calculate_metrics(solution, inp)

    return {
        "timeseries": solution,
        "metrics": metrics
    }


def run_comparison(
    days: int = 7,
    season: str = "dry",
    solver: str = "highs",
    output_dir: str = "python-optimizer/results"
) -> Dict:
    """
    Run multi-day comparison between baseline and KORA.

    Args:
        days: Number of days to simulate
        season: "dry" or "wet" (Madagascar seasons)
        solver: Optimization solver to use
        output_dir: Where to save results

    Returns:
        Dictionary with comparison results
    """

    specs = MahavelonaSpecs()
    fares = MahavelonaFareStructure()

    print("=" * 60)
    print("KORA MAHAVELONA PILOT SIMULATION")
    print("=" * 60)
    print(f"Microgrid: {specs.pv_capacity_kw} kWp solar, {specs.battery_capacity_kwh} kWh battery")
    print(f"Customers: {specs.total_customers} connections")
    print(f"Baseline curtailment: {specs.baseline_curtailment_rate * 100}%")
    print(f"Simulating {days} days ({season} season)")
    print("=" * 60)
    print()

    # Storage for daily results
    baseline_daily = []
    kora_daily = []

    for day in range(days):
        print(f"Day {day + 1}/{days}...", end=" ")

        # Generate daily profiles
        day_type = "clear" if np.random.random() > 0.2 else "partly_cloudy"  # 80% clear days
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

        # Simulate baseline
        baseline_result = simulate_baseline(solar, demand, specs, fares)
        baseline_daily.append(baseline_result)

        # Simulate KORA
        kora_result = simulate_kora(solar, demand, specs, fares, solver=solver)
        kora_daily.append(kora_result)

        print(f"Baseline curtailment: {baseline_result['metrics']['curtailment_rate']*100:.1f}%, "
              f"KORA curtailment: {kora_result['metrics']['curtailment_rate']*100:.1f}%")

    print()
    print("=" * 60)
    print("SUMMARY RESULTS")
    print("=" * 60)

    # Aggregate metrics
    def aggregate_metrics(daily_results):
        total_pv = sum(d["metrics"]["total_pv_kwh"] for d in daily_results)
        total_curtail = sum(d["metrics"]["total_curtail_kwh"] for d in daily_results)
        total_served = sum(d["metrics"]["total_demand_served_kwh"] for d in daily_results)
        total_unmet = sum(d["metrics"]["total_unmet_kwh"] for d in daily_results)
        total_revenue = sum(d["metrics"]["total_revenue_ariary"] for d in daily_results)
        total_blackout_hours = sum(d["metrics"]["blackout_hours"] for d in daily_results)

        return {
            "total_pv_kwh": total_pv,
            "total_curtail_kwh": total_curtail,
            "curtailment_rate": total_curtail / total_pv if total_pv > 0 else 0,
            "total_demand_served_kwh": total_served,
            "total_unmet_kwh": total_unmet,
            "total_revenue_ariary": total_revenue,
            "avg_price_ariary": total_revenue / total_served if total_served > 0 else 0,
            "total_blackout_hours": total_blackout_hours,
        }

    baseline_summary = aggregate_metrics(baseline_daily)
    kora_summary = aggregate_metrics(kora_daily)

    # Print comparison
    print("\nBASELINE (Current Operation):")
    print(f"  Total PV production: {baseline_summary['total_pv_kwh']:.1f} kWh")
    print(f"  Curtailment: {baseline_summary['total_curtail_kwh']:.1f} kWh ({baseline_summary['curtailment_rate']*100:.1f}%)")
    print(f"  Demand served: {baseline_summary['total_demand_served_kwh']:.1f} kWh")
    print(f"  Unmet demand: {baseline_summary['total_unmet_kwh']:.1f} kWh")
    print(f"  Revenue: {baseline_summary['total_revenue_ariary']:,.0f} Ar (${baseline_summary['total_revenue_ariary']/4500:.0f})")
    print(f"  Avg price: {baseline_summary['avg_price_ariary']:.0f} Ar/kWh")
    print(f"  Blackout hours: {baseline_summary['total_blackout_hours']}")

    print("\nKORA (Optimized):")
    print(f"  Total PV production: {kora_summary['total_pv_kwh']:.1f} kWh")
    print(f"  Curtailment: {kora_summary['total_curtail_kwh']:.1f} kWh ({kora_summary['curtailment_rate']*100:.1f}%)")
    print(f"  Demand served: {kora_summary['total_demand_served_kwh']:.1f} kWh")
    print(f"  Unmet demand: {kora_summary['total_unmet_kwh']:.1f} kWh")
    print(f"  Revenue: {kora_summary['total_revenue_ariary']:,.0f} Ar (${kora_summary['total_revenue_ariary']/4500:.0f})")
    print(f"  Avg price: {kora_summary['avg_price_ariary']:.0f} Ar/kWh")
    print(f"  Blackout hours: {kora_summary['total_blackout_hours']}")

    print("\nIMPACT:")
    curtail_reduction = baseline_summary['total_curtail_kwh'] - kora_summary['total_curtail_kwh']
    curtail_reduction_pct = (1 - kora_summary['curtailment_rate'] / baseline_summary['curtailment_rate']) * 100 if baseline_summary['curtailment_rate'] > 0 else 0
    revenue_increase = kora_summary['total_revenue_ariary'] - baseline_summary['total_revenue_ariary']
    revenue_increase_pct = revenue_increase / baseline_summary['total_revenue_ariary'] * 100 if baseline_summary['total_revenue_ariary'] > 0 else 0
    kwh_increase = kora_summary['total_demand_served_kwh'] - baseline_summary['total_demand_served_kwh']
    price_decrease = kora_summary['avg_price_ariary'] - baseline_summary['avg_price_ariary']
    price_decrease_pct = price_decrease / baseline_summary['avg_price_ariary'] * 100 if baseline_summary['avg_price_ariary'] > 0 else 0

    print(f"  ✅ Curtailment reduced by {curtail_reduction:.1f} kWh ({curtail_reduction_pct:.1f}%)")
    print(f"  ✅ Revenue increased by {revenue_increase:,.0f} Ar/week (${revenue_increase/4500:.0f}/week, ${revenue_increase*52/4500/12:.0f}/month)")
    print(f"  ✅ Energy sales increased by {kwh_increase:.1f} kWh ({kwh_increase/baseline_summary['total_demand_served_kwh']*100:.1f}%)")
    print(f"  ✅ Customer price {'decreased' if price_decrease < 0 else 'increased'} by {abs(price_decrease):.0f} Ar/kWh ({abs(price_decrease_pct):.1f}%)")
    print(f"  ✅ Blackouts reduced by {baseline_summary['total_blackout_hours'] - kora_summary['total_blackout_hours']} hours")

    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save detailed comparison
    comparison = {
        "config": {
            "days": days,
            "season": season,
            "pv_capacity_kw": specs.pv_capacity_kw,
            "battery_capacity_kwh": specs.battery_capacity_kwh,
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
            "curtailment_reduction_pct": curtail_reduction_pct,
            "revenue_increase_ariary": revenue_increase,
            "revenue_increase_pct": revenue_increase_pct,
            "kwh_increase": kwh_increase,
            "price_change_ariary": price_decrease,
            "price_change_pct": price_decrease_pct,
        }
    }

    json_path = output_path / "mahavelona_comparison.json"
    with open(json_path, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\n✅ Results saved to {json_path}")

    # Save CSV for easy plotting (first day only)
    csv_path = output_path / "day1_timeseries.csv"
    with open(csv_path, "w") as f:
        f.write("hour,solar_kw,baseline_demand_kw,baseline_price_ar,baseline_curtail_kw,baseline_soc_kwh,")
        f.write("kora_demand_kw,kora_price_ar,kora_curtail_kw,kora_soc_kwh,kora_charge_kw,kora_discharge_kw\n")

        for h in range(24):
            solar = baseline_daily[0]["timeseries"]["demand_kw"][h] + \
                    baseline_daily[0]["timeseries"]["p_charge_kw"][h] - \
                    baseline_daily[0]["timeseries"]["p_discharge_kw"][h] + \
                    baseline_daily[0]["timeseries"]["p_curtail_kw"][h]

            f.write(f"{h},")
            f.write(f"{solar:.2f},")
            f.write(f"{baseline_daily[0]['timeseries']['demand_kw'][h]:.2f},")
            f.write(f"{baseline_daily[0]['timeseries']['price_ariary'][h]:.0f},")
            f.write(f"{baseline_daily[0]['timeseries']['p_curtail_kw'][h]:.2f},")
            f.write(f"{baseline_daily[0]['timeseries']['soc_kwh'][h]:.2f},")
            f.write(f"{kora_daily[0]['timeseries']['demand_kw'][h]:.2f},")
            f.write(f"{kora_daily[0]['timeseries']['price_ariary'][h]:.0f},")
            f.write(f"{kora_daily[0]['timeseries']['p_curtail_kw'][h]:.2f},")
            f.write(f"{kora_daily[0]['timeseries']['soc_kwh'][h]:.2f},")
            f.write(f"{kora_daily[0]['timeseries']['p_charge_kw'][h]:.2f},")
            f.write(f"{kora_daily[0]['timeseries']['p_discharge_kw'][h]:.2f}\n")

    print(f"✅ Day 1 time-series saved to {csv_path}")

    return comparison


def main():
    parser = argparse.ArgumentParser(description="Run Mahavelona pilot simulation")
    parser.add_argument("--days", type=int, default=7, help="Number of days to simulate")
    parser.add_argument("--season", type=str, default="dry", choices=["dry", "wet"], help="Madagascar season")
    parser.add_argument("--solver", type=str, default="highs", help="Optimization solver")
    parser.add_argument("--output", type=str, default="python-optimizer/results", help="Output directory")

    args = parser.parse_args()

    run_comparison(
        days=args.days,
        season=args.season,
        solver=args.solver,
        output_dir=args.output
    )


if __name__ == "__main__":
    main()
