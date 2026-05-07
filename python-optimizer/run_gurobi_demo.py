#!/usr/bin/env python
"""
KORA Gurobi Optimizer Demo

Demonstrates the production-ready Gurobi-based optimizer with
real Mahavelona microgrid specifications.

This script:
1. Checks Gurobi availability and license status
2. Generates realistic Madagascar solar/demand profiles
3. Runs the optimizer (Gurobi or GLPK fallback)
4. Shows detailed results including curtailment reduction

Usage:
    python run_gurobi_demo.py                    # Auto-select solver
    python run_gurobi_demo.py --solver gurobi    # Force Gurobi
    python run_gurobi_demo.py --solver glpk      # Force GLPK (linear model)
    python run_gurobi_demo.py --hours 48         # 2-day horizon
    python run_gurobi_demo.py --benchmark        # Compare Gurobi vs GLPK
"""

import argparse
import sys
import time
import numpy as np

# Add parent directory for imports
sys.path.insert(0, '.')

from optimizer.gurobi_model import (
    GUROBI_AVAILABLE,
    check_gurobi_license,
    GurobiSolution,
    solve_kora_model,
    extract_kora_solution,
    calculate_metrics,
    KoraOptimizerInputs,
)

from mahavelona_config import (
    MahavelonaSpecs,
    MahavelonaFareStructure,
    generate_madagascar_solar_profile,
    generate_madagascar_demand_profile,
)


def print_header(title: str) -> None:
    """Print a formatted header."""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def print_section(title: str) -> None:
    """Print a section header."""
    print()
    print(f"--- {title} ---")


def check_solvers() -> dict:
    """Check available solvers and return status dict."""
    status = {
        "gurobi_installed": GUROBI_AVAILABLE,
        "gurobi_licensed": False,
        "gurobi_message": "",
        "glpk_available": True,  # GLPK is the fallback solver
    }

    if GUROBI_AVAILABLE:
        is_valid, msg = check_gurobi_license()
        status["gurobi_licensed"] = is_valid
        status["gurobi_message"] = msg

    return status


def create_inputs(specs: MahavelonaSpecs, hours: int) -> KoraOptimizerInputs:
    """Create optimizer inputs from Mahavelona specs."""
    # Fix random seed for reproducibility
    np.random.seed(42)

    solar = generate_madagascar_solar_profile(
        peak_capacity_kw=specs.pv_capacity_kw,
        hours=hours,
        season="dry",
        day_type="clear"
    )

    demand = generate_madagascar_demand_profile(
        total_customers=specs.total_customers,
        peak_load_kw=53,  # Known peak load
        hours=hours,
        day_type="weekday"
    )

    return KoraOptimizerInputs(
        pv_forecast_kw=solar.tolist(),
        base_demand_kw=demand.tolist(),
        battery_capacity_kwh=specs.battery_capacity_kwh,
        battery_power_kw=specs.battery_power_kw,
        soc_init_kwh=specs.battery_capacity_kwh * 0.3,  # Start at 30%
        soc_min_kwh=specs.battery_capacity_kwh * specs.soc_min_percent / 100,
        soc_max_kwh=specs.battery_capacity_kwh * specs.soc_max_percent / 100,
        eta_charge=specs.battery_efficiency_charge,
        eta_discharge=specs.battery_efficiency_discharge,
        battery_cycle_cost_per_kwh=0.01,
        price_min=1000,  # 1000 Ar/kWh minimum
        price_max=2500,  # 2500 Ar/kWh maximum
        price_reference=1750,  # Reference price
        demand_elasticity=0.6,  # 10% price drop = 6% demand increase
        curtailment_value_per_kwh=1500,  # Value of curtailed energy
        blackout_penalty_per_kwh=5000,  # High penalty for blackouts
        timestep_hours=1.0,
        target_soc_end_kwh=specs.battery_capacity_kwh * 0.3,  # End at 30%
    )


def run_optimization(
    inputs: KoraOptimizerInputs,
    solver: str,
    time_limit: int
) -> tuple:
    """Run optimization and return (result, solution_dict, metrics, solve_time)."""
    start = time.time()
    result = solve_kora_model(inputs, solver=solver, time_limit_sec=time_limit)
    solve_time = time.time() - start

    solution = extract_kora_solution(result)
    metrics = calculate_metrics(solution, inputs)

    return result, solution, metrics, solve_time


def print_results(
    result,
    solution: dict,
    metrics: dict,
    solve_time: float,
    inputs: KoraOptimizerInputs,
    baseline_curtailment: float = 0.70
) -> None:
    """Print detailed optimization results."""

    print_section("Solver Information")
    if isinstance(result, GurobiSolution):
        print(f"  Solver:           Gurobi")
        print(f"  Status:           {result.status}")
        print(f"  Solve time:       {result.solve_time_sec:.2f} seconds")
        if result.mip_gap is not None:
            print(f"  MIP gap:          {result.mip_gap*100:.2f}%")
        print(f"  Objective value:  {result.objective_value:,.0f}")
    else:
        print(f"  Solver:           GLPK (via Pyomo)")
        print(f"  Solve time:       {solve_time:.2f} seconds")

    print_section("Energy Metrics")
    print(f"  Total PV generation:    {metrics['total_pv_kwh']:,.1f} kWh")
    print(f"  Energy curtailed:       {metrics['total_curtail_kwh']:,.1f} kWh")
    print(f"  Curtailment rate:       {metrics['curtailment_rate']*100:.1f}%")
    print(f"  Demand served:          {metrics['total_demand_served_kwh']:,.1f} kWh")
    print(f"  Unmet demand:           {metrics['total_unmet_kwh']:,.1f} kWh")
    print(f"  Blackout hours:         {metrics['blackout_hours']}")
    print(f"  Battery cycles:         {metrics['battery_cycles']:.2f}")

    print_section("Financial Metrics")
    print(f"  Total revenue:          {metrics['total_revenue_ariary']:,.0f} Ariary")
    print(f"  Average price:          {metrics['avg_price_ariary']:,.0f} Ar/kWh")

    print_section("Improvement vs Baseline")
    improvement = (baseline_curtailment - metrics['curtailment_rate']) / baseline_curtailment * 100
    print(f"  Baseline curtailment:   {baseline_curtailment*100:.0f}%")
    print(f"  Optimized curtailment:  {metrics['curtailment_rate']*100:.1f}%")
    print(f"  Curtailment REDUCTION:  {improvement:.1f}%")

    if metrics['curtailment_rate'] < baseline_curtailment:
        print(f"  --> Saving {metrics['total_curtail_kwh'] - (sum(inputs.pv_forecast_kw) * baseline_curtailment):,.0f} kWh/day!")
    else:
        print(f"  --> WARNING: Curtailment not reduced!")


def print_hourly_schedule(
    solution: dict,
    inputs: KoraOptimizerInputs,
    hours: list = None
) -> None:
    """Print hourly schedule for selected hours."""
    if hours is None:
        hours = [6, 8, 10, 12, 14, 16, 18, 20, 22]

    print_section("Hourly Schedule (Sample Hours)")
    print("-" * 90)
    print(f"{'Hour':>5} {'PV kW':>10} {'Demand kW':>12} {'Price Ar':>10} {'Charge kW':>12} {'Curtail kW':>12} {'SOC kWh':>10}")
    print("-" * 90)

    for h in hours:
        if h < len(solution['price_ariary']):
            print(
                f"{h:5d} "
                f"{inputs.pv_forecast_kw[h]:10.1f} "
                f"{solution['demand_kw'][h]:12.1f} "
                f"{solution['price_ariary'][h]:10.0f} "
                f"{solution['p_charge_kw'][h]:12.1f} "
                f"{solution['p_curtail_kw'][h]:12.1f} "
                f"{solution['soc_kwh'][h]:10.1f}"
            )


def run_benchmark(inputs: KoraOptimizerInputs, time_limit: int) -> None:
    """Run performance benchmark comparing Gurobi vs GLPK."""
    print_header("PERFORMANCE BENCHMARK: Gurobi vs GLPK")

    solver_status = check_solvers()

    if not solver_status["gurobi_licensed"]:
        print("ERROR: Gurobi license required for benchmark")
        print(f"Status: {solver_status['gurobi_message']}")
        return

    # Run Gurobi
    print("\nRunning Gurobi...")
    gurobi_start = time.time()
    gurobi_result = solve_kora_model(inputs, solver="gurobi", time_limit_sec=time_limit)
    gurobi_time = time.time() - gurobi_start
    gurobi_metrics = calculate_metrics(extract_kora_solution(gurobi_result), inputs)

    # Run GLPK (using linearized model)
    print("Running GLPK...")
    glpk_start = time.time()
    glpk_result = solve_kora_model(inputs, solver="glpk", time_limit_sec=time_limit)
    glpk_time = time.time() - glpk_start
    glpk_metrics = calculate_metrics(extract_kora_solution(glpk_result), inputs)

    # Print comparison
    print()
    print("-" * 70)
    print(f"{'Metric':<30} {'Gurobi':>18} {'GLPK':>18}")
    print("-" * 70)
    print(f"{'Solve time (s)':<30} {gurobi_time:>18.2f} {glpk_time:>18.2f}")
    print(f"{'Curtailment (%)':<30} {gurobi_metrics['curtailment_rate']*100:>18.1f} {glpk_metrics['curtailment_rate']*100:>18.1f}")
    print(f"{'Revenue (Ar)':<30} {gurobi_metrics['total_revenue_ariary']:>18,.0f} {glpk_metrics['total_revenue_ariary']:>18,.0f}")
    print(f"{'Avg price (Ar/kWh)':<30} {gurobi_metrics['avg_price_ariary']:>18.0f} {glpk_metrics['avg_price_ariary']:>18.0f}")
    print(f"{'Blackout hours':<30} {gurobi_metrics['blackout_hours']:>18d} {glpk_metrics['blackout_hours']:>18d}")
    print("-" * 70)

    if gurobi_time < glpk_time:
        speedup = glpk_time / gurobi_time
        print(f"\nGurobi is {speedup:.1f}x FASTER than GLPK")
    else:
        speedup = gurobi_time / glpk_time
        print(f"\nGLPK is {speedup:.1f}x faster than Gurobi")

    # Solution quality comparison
    if abs(gurobi_metrics['total_revenue_ariary'] - glpk_metrics['total_revenue_ariary']) < 10:
        print("Solution quality: EQUIVALENT")
    elif gurobi_metrics['total_revenue_ariary'] > glpk_metrics['total_revenue_ariary']:
        diff = (gurobi_metrics['total_revenue_ariary'] / glpk_metrics['total_revenue_ariary'] - 1) * 100
        print(f"Solution quality: Gurobi finds {diff:.1f}% BETTER solution")
    else:
        diff = (glpk_metrics['total_revenue_ariary'] / gurobi_metrics['total_revenue_ariary'] - 1) * 100
        print(f"Solution quality: GLPK finds {diff:.1f}% better solution")


def main():
    parser = argparse.ArgumentParser(
        description="KORA Gurobi Optimizer Demo - Mahavelona Microgrid",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_gurobi_demo.py                    # Auto-select best solver
    python run_gurobi_demo.py --solver gurobi    # Force Gurobi
    python run_gurobi_demo.py --solver glpk      # Force GLPK (linear model)
    python run_gurobi_demo.py --hours 48         # 2-day optimization horizon
    python run_gurobi_demo.py --benchmark        # Compare Gurobi vs GLPK
        """
    )
    parser.add_argument(
        "--solver",
        default="auto",
        choices=["auto", "gurobi", "glpk"],
        help="Solver to use (default: auto)"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Optimization horizon in hours (default: 24)"
    )
    parser.add_argument(
        "--time-limit",
        type=int,
        default=60,
        help="Solver time limit in seconds (default: 60)"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run Gurobi vs HiGHS benchmark"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show solver output"
    )

    args = parser.parse_args()

    # Print header
    print_header("KORA GUROBI OPTIMIZER DEMO")
    print("Mahavelona Microgrid - Africa GreenTec Madagascar")

    # Check solver availability
    print_section("Solver Availability")
    solver_status = check_solvers()
    print(f"  Gurobi installed:   {'Yes' if solver_status['gurobi_installed'] else 'No'}")
    if solver_status['gurobi_installed']:
        print(f"  Gurobi licensed:    {'Yes' if solver_status['gurobi_licensed'] else 'No'}")
        print(f"  License status:     {solver_status['gurobi_message']}")
    print(f"  GLPK available:     Yes (via Pyomo)")

    # Load Mahavelona specs
    specs = MahavelonaSpecs()
    fares = MahavelonaFareStructure()

    print_section("Site Configuration")
    print(f"  Site:               Mahavelona, Itasy region, Madagascar")
    print(f"  Solar capacity:     {specs.pv_capacity_kw} kWp")
    print(f"  Battery capacity:   {specs.battery_capacity_kwh} kWh")
    print(f"  Battery power:      {specs.battery_power_kw} kW")
    print(f"  Customers:          {specs.total_customers}")
    print(f"  Peak load:          53 kW")
    print(f"  Baseline curtailment: {specs.baseline_curtailment_rate*100:.0f}%")

    print_section("Pricing Configuration")
    print(f"  Price range:        1000 - 2500 Ar/kWh")
    print(f"  Reference price:    1750 Ar/kWh")
    print(f"  Demand elasticity:  0.6 (10% price drop = 6% demand increase)")

    # Create inputs
    print_section("Generating Scenario Data")
    print(f"  Horizon:            {args.hours} hours")
    print(f"  Season:             Dry (high solar)")
    print(f"  Day type:           Clear sky, weekday demand")

    inputs = create_inputs(specs, args.hours)

    print(f"  Total PV forecast:  {sum(inputs.pv_forecast_kw):.0f} kWh")
    print(f"  Total demand base:  {sum(inputs.base_demand_kw):.0f} kWh")

    # Run benchmark mode
    if args.benchmark:
        run_benchmark(inputs, args.time_limit)
        return

    # Run optimization
    print_section(f"Running Optimization (solver={args.solver})")
    print(f"  Time limit:         {args.time_limit} seconds")

    result, solution, metrics, solve_time = run_optimization(
        inputs, args.solver, args.time_limit
    )

    # Print results
    print_header("OPTIMIZATION RESULTS")
    print_results(result, solution, metrics, solve_time, inputs, specs.baseline_curtailment_rate)

    # Print hourly schedule
    print_hourly_schedule(solution, inputs)

    # Summary
    print_header("SUMMARY")
    if metrics['curtailment_rate'] < specs.baseline_curtailment_rate:
        improvement = (specs.baseline_curtailment_rate - metrics['curtailment_rate']) / specs.baseline_curtailment_rate * 100
        saved_kwh = (specs.baseline_curtailment_rate - metrics['curtailment_rate']) * sum(inputs.pv_forecast_kw)
        print(f"SUCCESS! KORA optimizer reduces curtailment by {improvement:.0f}%")
        print(f"This saves approximately {saved_kwh:.0f} kWh per day")
        print(f"Additional revenue potential: {saved_kwh * 1750:,.0f} Ar/day")
    else:
        print("WARNING: Curtailment not reduced - check scenario parameters")

    print()
    print("To run with different settings:")
    print("  python run_gurobi_demo.py --solver gurobi --hours 48 --time-limit 120")
    print()


if __name__ == "__main__":
    main()
