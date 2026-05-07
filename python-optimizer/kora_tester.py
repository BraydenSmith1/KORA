#!/usr/bin/env python
"""
KORA Optimizer Terminal Tester

Interactive terminal tool for testing the KORA optimizer with full visibility into:
- Decision variables (price, battery dispatch, demand response)
- Constraints (battery physics, power balance, price bounds)
- Objective function breakdown
- Baseline vs optimized comparison
- Scenario modeling (weather, demand, elasticity)

Usage:
    python kora_tester.py                     # Interactive mode
    python kora_tester.py --scenario cloudy   # Run specific scenario
    python kora_tester.py --elasticity 0.3    # Override elasticity
    python kora_tester.py --export results/   # Export results to CSV

Requirements:
    pip install rich numpy
"""

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' not installed. Install with: pip install rich")
    print("Falling back to basic output.\n")

from optimizer.gurobi_model import (
    GUROBI_AVAILABLE,
    check_gurobi_license,
    solve_kora_model,
    extract_kora_solution,
    calculate_metrics,
    KoraOptimizerInputs,
)

from mahavelona_config import (
    MahavelonaSpecs,
    generate_madagascar_solar_profile,
    generate_madagascar_demand_profile,
)


# =============================================================================
# Console Setup
# =============================================================================

console = Console() if RICH_AVAILABLE else None


def print_rich(content, **kwargs):
    """Print using rich if available, else fallback to print."""
    if console:
        console.print(content, **kwargs)
    else:
        print(content)


# =============================================================================
# Scenario Definitions
# =============================================================================

@dataclass
class Scenario:
    """Test scenario configuration."""
    name: str
    description: str

    # Solar parameters
    season: str = "dry"  # dry, wet
    day_type: str = "clear"  # clear, partly_cloudy, cloudy, intermittent
    pv_capacity_kw: float = 118.5

    # Demand parameters
    peak_load_kw: float = 53.0
    demand_type: str = "weekday"  # weekday, weekend, holiday, spike
    demand_multiplier: float = 1.0

    # Battery parameters
    battery_capacity_kwh: float = 115.0
    battery_power_kw: float = 54.0
    initial_soc_pct: float = 30.0

    # Pricing parameters
    price_min: float = 1000.0
    price_max: float = 2500.0
    price_reference: float = 1750.0

    # Demand response
    elasticity: float = 0.6

    # Penalties
    curtailment_penalty: float = 1500.0
    blackout_penalty: float = 5000.0

    # Solver
    solver: str = "auto"
    time_limit_sec: int = 60


# Pre-defined scenarios
SCENARIOS = {
    "baseline": Scenario(
        name="Baseline (Clear Day)",
        description="Typical clear day with normal demand - best case for solar",
        season="dry", day_type="clear", demand_type="weekday"
    ),
    "cloudy": Scenario(
        name="Cloudy Day",
        description="Overcast conditions - 30-40% solar reduction",
        season="wet", day_type="cloudy", demand_type="weekday"
    ),
    "partly_cloudy": Scenario(
        name="Partly Cloudy",
        description="Variable clouds - intermittent solar production",
        season="dry", day_type="partly_cloudy", demand_type="weekday"
    ),
    "wet_season": Scenario(
        name="Wet Season",
        description="Rainy season with reduced solar and variable clouds",
        season="wet", day_type="partly_cloudy", demand_type="weekday"
    ),
    "weekend": Scenario(
        name="Weekend",
        description="Lower SME activity, higher household usage",
        season="dry", day_type="clear", demand_type="weekend",
        demand_multiplier=0.85
    ),
    "high_demand": Scenario(
        name="High Demand Day",
        description="Festival or market day - 130% normal demand",
        season="dry", day_type="clear", demand_type="weekday",
        demand_multiplier=1.3
    ),
    "low_elasticity": Scenario(
        name="Low Price Sensitivity",
        description="Customers less responsive to price signals",
        season="dry", day_type="clear", elasticity=0.3
    ),
    "high_elasticity": Scenario(
        name="High Price Sensitivity",
        description="Customers very responsive to price signals",
        season="dry", day_type="clear", elasticity=0.8
    ),
    "battery_degraded": Scenario(
        name="Degraded Battery",
        description="Battery at 70% original capacity",
        season="dry", day_type="clear",
        battery_capacity_kwh=80.5, battery_power_kw=38.0
    ),
    "narrow_price_band": Scenario(
        name="Narrow Price Band",
        description="Tight price constraints (1500-2000 Ar/kWh)",
        season="dry", day_type="clear",
        price_min=1500, price_max=2000
    ),
    "wide_price_band": Scenario(
        name="Wide Price Band",
        description="Aggressive pricing allowed (500-3500 Ar/kWh)",
        season="dry", day_type="clear",
        price_min=500, price_max=3500
    ),
    "low_battery": Scenario(
        name="Low Initial Battery",
        description="Starting with nearly empty battery (10%)",
        season="dry", day_type="clear",
        initial_soc_pct=10.0
    ),
    "full_battery": Scenario(
        name="Full Initial Battery",
        description="Starting with full battery (90%)",
        season="dry", day_type="clear",
        initial_soc_pct=90.0
    ),
    "stress_test": Scenario(
        name="Stress Test",
        description="Worst case: cloudy day, high demand, low battery, tight prices",
        season="wet", day_type="cloudy",
        demand_multiplier=1.3, initial_soc_pct=15.0,
        price_min=1500, price_max=2200
    ),
}


# =============================================================================
# Data Generation
# =============================================================================

def generate_solar_profile(scenario: Scenario, hours: int = 24) -> np.ndarray:
    """Generate solar profile based on scenario."""
    np.random.seed(42)  # Reproducibility

    if scenario.day_type == "intermittent":
        # Generate clear day then add cloud events
        solar = generate_madagascar_solar_profile(
            peak_capacity_kw=scenario.pv_capacity_kw,
            hours=hours,
            season=scenario.season,
            day_type="clear"
        )
        # Add cloud events at random hours
        for h in [9, 10, 14, 15]:
            if h < hours:
                solar[h] *= 0.2
        return solar
    else:
        return generate_madagascar_solar_profile(
            peak_capacity_kw=scenario.pv_capacity_kw,
            hours=hours,
            season=scenario.season,
            day_type=scenario.day_type
        )


def generate_demand_profile(scenario: Scenario, hours: int = 24) -> np.ndarray:
    """Generate demand profile based on scenario."""
    np.random.seed(42)  # Reproducibility

    demand = generate_madagascar_demand_profile(
        total_customers=251,
        peak_load_kw=scenario.peak_load_kw,
        hours=hours,
        day_type=scenario.demand_type
    )

    return demand * scenario.demand_multiplier


def create_optimizer_inputs(
    scenario: Scenario,
    solar: np.ndarray,
    demand: np.ndarray
) -> KoraOptimizerInputs:
    """Create optimizer inputs from scenario and profiles."""
    return KoraOptimizerInputs(
        pv_forecast_kw=solar.tolist(),
        base_demand_kw=demand.tolist(),
        battery_capacity_kwh=scenario.battery_capacity_kwh,
        battery_power_kw=scenario.battery_power_kw,
        soc_init_kwh=scenario.battery_capacity_kwh * scenario.initial_soc_pct / 100,
        soc_min_kwh=scenario.battery_capacity_kwh * 0.20,
        soc_max_kwh=scenario.battery_capacity_kwh * 0.95,
        eta_charge=0.94,
        eta_discharge=0.94,
        battery_cycle_cost_per_kwh=0.01,
        price_min=scenario.price_min,
        price_max=scenario.price_max,
        price_reference=scenario.price_reference,
        demand_elasticity=scenario.elasticity,
        curtailment_value_per_kwh=scenario.curtailment_penalty,
        blackout_penalty_per_kwh=scenario.blackout_penalty,
        timestep_hours=1.0,
        target_soc_end_kwh=scenario.battery_capacity_kwh * 0.30,
    )


# =============================================================================
# Baseline Calculation (No Optimization)
# =============================================================================

def calculate_baseline(
    solar: np.ndarray,
    demand: np.ndarray,
    scenario: Scenario
) -> Dict[str, Any]:
    """Calculate baseline performance (fixed pricing, naive dispatch)."""
    hours = len(solar)
    battery_capacity = scenario.battery_capacity_kwh
    battery_power = scenario.battery_power_kw
    soc_min = battery_capacity * 0.20
    soc_max = battery_capacity * 0.95

    # Track state
    soc = battery_capacity * scenario.initial_soc_pct / 100

    total_curtailment = 0
    total_unmet = 0
    total_revenue = 0
    total_demand_served = 0

    hourly_data = []

    for h in range(hours):
        pv = solar[h]
        load = demand[h]

        # Power balance with fixed price (no demand response)
        excess = pv - load

        if excess > 0:
            # Excess solar - try to charge battery
            charge_room = soc_max - soc
            charge_power = min(excess, battery_power, charge_room / 0.94)
            actual_charge = charge_power * 0.94
            soc += actual_charge
            curtailed = excess - charge_power
            total_curtailment += curtailed
            discharge = 0
            unmet = 0
        else:
            # Deficit - discharge battery
            deficit = -excess
            discharge_room = soc - soc_min
            discharge_power = min(deficit, battery_power, discharge_room * 0.94)
            actual_discharge = discharge_power / 0.94
            soc -= actual_discharge
            unmet = deficit - discharge_power
            total_unmet += unmet
            curtailed = 0
            charge_power = 0
            discharge = discharge_power

        # Revenue at fixed reference price
        served = load - unmet
        revenue = served * scenario.price_reference
        total_demand_served += served
        total_revenue += revenue

        hourly_data.append({
            "hour": h,
            "pv_kw": pv,
            "demand_kw": load,
            "price_ariary": scenario.price_reference,
            "charge_kw": charge_power if excess > 0 else 0,
            "discharge_kw": discharge,
            "soc_kwh": soc,
            "curtail_kw": curtailed,
            "unmet_kw": unmet,
        })

    total_pv = sum(solar)

    return {
        "total_pv_kwh": total_pv,
        "total_curtail_kwh": total_curtailment,
        "curtailment_rate": total_curtailment / total_pv if total_pv > 0 else 0,
        "total_unmet_kwh": total_unmet,
        "blackout_hours": sum(1 for d in hourly_data if d["unmet_kw"] > 0.1),
        "total_demand_served_kwh": total_demand_served,
        "total_revenue_ariary": total_revenue,
        "avg_price_ariary": scenario.price_reference,
        "hourly_data": hourly_data,
    }


# =============================================================================
# Display Functions
# =============================================================================

def display_scenario_info(scenario: Scenario):
    """Display scenario configuration."""
    if not RICH_AVAILABLE:
        print(f"\n=== {scenario.name} ===")
        print(f"{scenario.description}\n")
        return

    table = Table(title=f"Scenario: {scenario.name}", box=box.ROUNDED)
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Description", style="dim")

    table.add_row("Season", scenario.season, "dry=high solar, wet=reduced")
    table.add_row("Day Type", scenario.day_type, "clear/partly_cloudy/cloudy")
    table.add_row("PV Capacity", f"{scenario.pv_capacity_kw} kWp", "Peak solar capacity")
    table.add_row("Peak Load", f"{scenario.peak_load_kw} kW", "Maximum demand")
    table.add_row("Demand Mult.", f"{scenario.demand_multiplier:.1f}x", "Demand scaling factor")
    table.add_row("", "", "")
    table.add_row("Battery Cap.", f"{scenario.battery_capacity_kwh} kWh", "Energy storage")
    table.add_row("Battery Power", f"{scenario.battery_power_kw} kW", "Max charge/discharge")
    table.add_row("Initial SOC", f"{scenario.initial_soc_pct}%", "Starting battery level")
    table.add_row("", "", "")
    table.add_row("Price Min", f"{scenario.price_min:.0f} Ar/kWh", "Floor price")
    table.add_row("Price Max", f"{scenario.price_max:.0f} Ar/kWh", "Ceiling price")
    table.add_row("Ref. Price", f"{scenario.price_reference:.0f} Ar/kWh", "Baseline price")
    table.add_row("Elasticity", f"{scenario.elasticity:.2f}", "Price sensitivity (0-1)")

    console.print(table)
    console.print(f"\n[dim]{scenario.description}[/dim]\n")


def display_model_formulation(scenario: Scenario):
    """Display the mathematical formulation."""
    if not RICH_AVAILABLE:
        print("\n=== OPTIMIZATION MODEL ===\n")
        print("Decision Variables:")
        print("  price[t]      - Hourly price (1000-2500 Ar/kWh)")
        print("  charge[t]     - Battery charge power (0-54 kW)")
        print("  discharge[t]  - Battery discharge power (0-54 kW)")
        print("  soc[t]        - State of charge (23-109 kWh)")
        return

    # Decision Variables
    vars_text = """
[bold cyan]DECISION VARIABLES[/bold cyan]
┌─────────────────┬──────────────────────────────────────────────┐
│ price[t]        │ Electricity price at hour t                  │
│                 │ Bounds: [{price_min:.0f}, {price_max:.0f}] Ar/kWh              │
├─────────────────┼──────────────────────────────────────────────┤
│ charge[t]       │ Battery charging power at hour t             │
│                 │ Bounds: [0, {battery_power:.0f}] kW                       │
├─────────────────┼──────────────────────────────────────────────┤
│ discharge[t]    │ Battery discharging power at hour t          │
│                 │ Bounds: [0, {battery_power:.0f}] kW                       │
├─────────────────┼──────────────────────────────────────────────┤
│ soc[t]          │ Battery state of charge at hour t            │
│                 │ Bounds: [{soc_min:.0f}, {soc_max:.0f}] kWh                    │
├─────────────────┼──────────────────────────────────────────────┤
│ demand[t]       │ Price-responsive demand at hour t            │
│                 │ Depends on price via elasticity              │
├─────────────────┼──────────────────────────────────────────────┤
│ curtail[t]      │ Curtailed (wasted) solar at hour t           │
│                 │ Bounds: [0, ∞] kW                            │
├─────────────────┼──────────────────────────────────────────────┤
│ unmet[t]        │ Unmet demand (blackout) at hour t            │
│                 │ Bounds: [0, ∞] kW                            │
└─────────────────┴──────────────────────────────────────────────┘
""".format(
        price_min=scenario.price_min,
        price_max=scenario.price_max,
        battery_power=scenario.battery_power_kw,
        soc_min=scenario.battery_capacity_kwh * 0.20,
        soc_max=scenario.battery_capacity_kwh * 0.95,
    )

    constraints_text = """
[bold yellow]CONSTRAINTS[/bold yellow]

1. [bold]Battery SOC Dynamics[/bold]
   soc[t+1] = soc[t] + 0.94×charge[t] - discharge[t]/0.94

2. [bold]Charge/Discharge Exclusivity[/bold]
   charge[t] > 0  ⟹  discharge[t] = 0  (and vice versa)

3. [bold]Demand Response (Elasticity = {elasticity})[/bold]
   demand[t] = base_demand[t] × (1 - {elasticity} × (price[t] - {ref_price}) / {ref_price})

   Example: If price drops 20% below {ref_price} Ar:
            demand increases by {elasticity} × 20% = {demand_change:.0f}%

4. [bold]Power Balance[/bold]
   PV[t] + discharge[t] = demand[t] + charge[t] + curtail[t] - unmet[t]
""".format(
        elasticity=scenario.elasticity,
        ref_price=scenario.price_reference,
        demand_change=scenario.elasticity * 20,
    )

    objective_text = """
[bold green]OBJECTIVE FUNCTION[/bold green]

[bold]Maximize:[/bold]
    Revenue - Curtailment Cost - Blackout Penalty - Battery Wear

[bold]Expanded:[/bold]
    Σ price[t] × demand[t]              (Revenue - QUADRATIC!)
  - {curtail_penalty:.0f} × Σ curtail[t]              (Curtailment opportunity cost)
  - {blackout_penalty:.0f} × Σ unmet[t]                (Blackout penalty - very high!)
  - 0.01 × Σ (charge[t] + discharge[t]) (Battery degradation)

[dim]Note: price × demand is quadratic because demand depends on price.
This requires Gurobi or linearization for other solvers.[/dim]
""".format(
        curtail_penalty=scenario.curtailment_penalty,
        blackout_penalty=scenario.blackout_penalty,
    )

    console.print(Panel(vars_text.strip(), title="Variables", border_style="cyan"))
    console.print(Panel(constraints_text.strip(), title="Constraints", border_style="yellow"))
    console.print(Panel(objective_text.strip(), title="Objective", border_style="green"))


def display_input_profiles(solar: np.ndarray, demand: np.ndarray):
    """Display input PV and demand profiles."""
    if not RICH_AVAILABLE:
        print("\n=== INPUT PROFILES ===")
        print(f"{'Hour':>5} {'PV (kW)':>10} {'Demand (kW)':>12} {'Net (kW)':>10}")
        print("-" * 40)
        for h in range(len(solar)):
            net = solar[h] - demand[h]
            print(f"{h:5d} {solar[h]:10.1f} {demand[h]:12.1f} {net:10.1f}")
        return

    table = Table(title="Input Profiles (24 hours)", box=box.SIMPLE)
    table.add_column("Hour", style="dim", justify="right")
    table.add_column("PV (kW)", justify="right", style="yellow")
    table.add_column("Demand (kW)", justify="right", style="blue")
    table.add_column("Net (kW)", justify="right")
    table.add_column("Visual", justify="left")

    for h in range(min(24, len(solar))):
        pv = solar[h]
        dem = demand[h]
        net = pv - dem

        # Color net based on surplus/deficit
        if net > 10:
            net_style = "green"
            bar = "[green]" + "█" * min(int(net/10), 10) + "[/green]"
        elif net < -10:
            net_style = "red"
            bar = "[red]" + "█" * min(int(-net/10), 10) + "[/red]"
        else:
            net_style = "dim"
            bar = "[dim]─[/dim]"

        table.add_row(
            f"{h:02d}:00",
            f"{pv:.1f}",
            f"{dem:.1f}",
            f"[{net_style}]{net:+.1f}[/{net_style}]",
            bar
        )

    console.print(table)

    # Summary
    total_pv = sum(solar)
    total_demand = sum(demand)
    console.print(f"\n[bold]Totals:[/bold] PV={total_pv:.0f} kWh, Demand={total_demand:.0f} kWh, Net={total_pv-total_demand:+.0f} kWh")


def display_comparison(baseline: Dict, optimized: Dict, scenario: Scenario):
    """Display side-by-side comparison of baseline vs optimized."""
    if not RICH_AVAILABLE:
        print("\n=== RESULTS COMPARISON ===")
        print(f"{'Metric':<30} {'Baseline':>15} {'Optimized':>15} {'Improvement':>15}")
        print("-" * 75)
        return

    table = Table(title="Baseline vs KORA Optimized", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Baseline", justify="right", style="dim")
    table.add_column("KORA", justify="right", style="green")
    table.add_column("Change", justify="right")

    def format_change(base, opt, lower_is_better=False):
        if base == 0:
            return "[dim]N/A[/dim]"
        change = (opt - base) / base * 100
        if lower_is_better:
            change = -change
        if change > 0:
            return f"[green]+{abs(change):.1f}%[/green]"
        elif change < 0:
            return f"[red]{change:.1f}%[/red]"
        else:
            return "[dim]0%[/dim]"

    # Energy metrics
    table.add_row(
        "Total PV Generation",
        f"{baseline['total_pv_kwh']:.0f} kWh",
        f"{optimized['total_pv_kwh']:.0f} kWh",
        "[dim]Same[/dim]"
    )
    table.add_row(
        "Energy Curtailed",
        f"{baseline['total_curtail_kwh']:.0f} kWh",
        f"{optimized['total_curtail_kwh']:.0f} kWh",
        format_change(baseline['total_curtail_kwh'], optimized['total_curtail_kwh'], lower_is_better=True)
    )
    table.add_row(
        "Curtailment Rate",
        f"{baseline['curtailment_rate']*100:.1f}%",
        f"{optimized['curtailment_rate']*100:.1f}%",
        format_change(baseline['curtailment_rate'], optimized['curtailment_rate'], lower_is_better=True)
    )
    table.add_row(
        "Demand Served",
        f"{baseline['total_demand_served_kwh']:.0f} kWh",
        f"{optimized['total_demand_served_kwh']:.0f} kWh",
        format_change(baseline['total_demand_served_kwh'], optimized['total_demand_served_kwh'])
    )
    table.add_row(
        "Unmet Demand",
        f"{baseline['total_unmet_kwh']:.1f} kWh",
        f"{optimized['total_unmet_kwh']:.1f} kWh",
        format_change(baseline['total_unmet_kwh'], optimized['total_unmet_kwh'], lower_is_better=True)
    )
    table.add_row(
        "Blackout Hours",
        f"{baseline['blackout_hours']}",
        f"{optimized['blackout_hours']}",
        format_change(baseline['blackout_hours'], optimized['blackout_hours'], lower_is_better=True)
    )
    table.add_row("", "", "", "")

    # Financial metrics
    table.add_row(
        "Total Revenue",
        f"{baseline['total_revenue_ariary']:,.0f} Ar",
        f"{optimized['total_revenue_ariary']:,.0f} Ar",
        format_change(baseline['total_revenue_ariary'], optimized['total_revenue_ariary'])
    )
    table.add_row(
        "Average Price",
        f"{baseline['avg_price_ariary']:.0f} Ar/kWh",
        f"{optimized['avg_price_ariary']:.0f} Ar/kWh",
        format_change(baseline['avg_price_ariary'], optimized['avg_price_ariary'])
    )

    # Calculate daily revenue difference
    revenue_diff = optimized['total_revenue_ariary'] - baseline['total_revenue_ariary']
    annual_diff = revenue_diff * 365

    table.add_row("", "", "", "")
    table.add_row(
        "[bold]Daily Revenue Gain[/bold]",
        "",
        f"[bold green]+{revenue_diff:,.0f} Ar[/bold green]",
        f"[bold green]+${revenue_diff/4500:.2f}[/bold green]"  # Approx USD
    )
    table.add_row(
        "[bold]Annual Revenue Gain[/bold]",
        "",
        f"[bold green]+{annual_diff:,.0f} Ar[/bold green]",
        f"[bold green]+${annual_diff/4500:,.0f}[/bold green]"
    )

    console.print(table)


def display_hourly_results(solution: Dict, inputs: KoraOptimizerInputs, baseline: Dict):
    """Display hourly optimization results."""
    if not RICH_AVAILABLE:
        print("\n=== HOURLY SCHEDULE ===")
        return

    table = Table(title="Hourly Optimization Results", box=box.SIMPLE)
    table.add_column("Hour", style="dim", justify="right")
    table.add_column("PV", justify="right", style="yellow")
    table.add_column("Base Dem", justify="right", style="dim")
    table.add_column("Opt Dem", justify="right", style="blue")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Charge", justify="right", style="cyan")
    table.add_column("Disch", justify="right", style="magenta")
    table.add_column("SOC", justify="right")
    table.add_column("Curtail", justify="right", style="red")

    for h in range(min(24, len(solution['price_ariary']))):
        pv = inputs.pv_forecast_kw[h]
        base_dem = inputs.base_demand_kw[h]
        opt_dem = solution['demand_kw'][h]
        price = solution['price_ariary'][h]
        charge = solution['p_charge_kw'][h]
        discharge = solution['p_discharge_kw'][h]
        soc = solution['soc_kwh'][h]
        curtail = solution['p_curtail_kw'][h]

        # Price styling
        if price < inputs.price_reference * 0.9:
            price_style = "green"
        elif price > inputs.price_reference * 1.1:
            price_style = "red"
        else:
            price_style = "dim"

        # Demand change indicator
        dem_change = (opt_dem - base_dem) / base_dem * 100 if base_dem > 0 else 0
        if dem_change > 5:
            dem_indicator = f"[green]{opt_dem:.1f} ↑[/green]"
        elif dem_change < -5:
            dem_indicator = f"[red]{opt_dem:.1f} ↓[/red]"
        else:
            dem_indicator = f"{opt_dem:.1f}"

        table.add_row(
            f"{h:02d}:00",
            f"{pv:.1f}",
            f"{base_dem:.1f}",
            dem_indicator,
            f"[{price_style}]{price:.0f}[/{price_style}]",
            f"{charge:.1f}" if charge > 0.1 else "[dim]-[/dim]",
            f"{discharge:.1f}" if discharge > 0.1 else "[dim]-[/dim]",
            f"{soc:.0f}",
            f"{curtail:.1f}" if curtail > 0.1 else "[dim]-[/dim]",
        )

    console.print(table)
    console.print("\n[dim]Legend: Price colors show deviation from reference. Demand arrows show elasticity effect.[/dim]")


def display_solver_info(result, solve_time: float):
    """Display solver information."""
    if not RICH_AVAILABLE:
        print(f"\nSolver: completed in {solve_time:.2f}s")
        return

    info = f"[bold]Solver:[/bold] {'Gurobi' if hasattr(result, 'mip_gap') else 'HiGHS/GLPK'}\n"
    info += f"[bold]Status:[/bold] {result.status if hasattr(result, 'status') else 'optimal'}\n"
    info += f"[bold]Solve Time:[/bold] {solve_time:.2f} seconds\n"
    if hasattr(result, 'mip_gap') and result.mip_gap is not None:
        info += f"[bold]MIP Gap:[/bold] {result.mip_gap*100:.2f}%\n"
    if hasattr(result, 'objective_value'):
        info += f"[bold]Objective:[/bold] {result.objective_value:,.0f}"

    console.print(Panel(info, title="Solver Info", border_style="blue"))


# =============================================================================
# Export Functions
# =============================================================================

def export_results(
    scenario: Scenario,
    solar: np.ndarray,
    demand: np.ndarray,
    baseline: Dict,
    optimized: Dict,
    solution: Dict,
    output_dir: str
):
    """Export results to CSV and JSON files."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Export hourly data to CSV
    csv_path = Path(output_dir) / f"kora_results_{scenario.name.lower().replace(' ', '_')}_{timestamp}.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'hour', 'pv_kw', 'base_demand_kw', 'opt_demand_kw', 'price_ariary',
            'charge_kw', 'discharge_kw', 'soc_kwh', 'curtail_kw', 'unmet_kw'
        ])
        for h in range(len(solution['price_ariary'])):
            writer.writerow([
                h,
                solar[h],
                demand[h],
                solution['demand_kw'][h],
                solution['price_ariary'][h],
                solution['p_charge_kw'][h],
                solution['p_discharge_kw'][h],
                solution['soc_kwh'][h],
                solution['p_curtail_kw'][h],
                solution['p_unmet_kw'][h],
            ])

    # Export summary to JSON
    json_path = Path(output_dir) / f"kora_summary_{scenario.name.lower().replace(' ', '_')}_{timestamp}.json"
    summary = {
        "scenario": {
            "name": scenario.name,
            "description": scenario.description,
            "elasticity": scenario.elasticity,
            "price_min": scenario.price_min,
            "price_max": scenario.price_max,
        },
        "baseline": {k: v for k, v in baseline.items() if k != 'hourly_data'},
        "optimized": optimized,
        "improvement": {
            "curtailment_reduction_pct": (baseline['curtailment_rate'] - optimized['curtailment_rate']) / baseline['curtailment_rate'] * 100 if baseline['curtailment_rate'] > 0 else 0,
            "revenue_increase_pct": (optimized['total_revenue_ariary'] - baseline['total_revenue_ariary']) / baseline['total_revenue_ariary'] * 100 if baseline['total_revenue_ariary'] > 0 else 0,
            "daily_revenue_gain_ariary": optimized['total_revenue_ariary'] - baseline['total_revenue_ariary'],
            "annual_revenue_gain_ariary": (optimized['total_revenue_ariary'] - baseline['total_revenue_ariary']) * 365,
        }
    }
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print_rich(f"\n[green]Exported:[/green]")
    print_rich(f"  CSV: {csv_path}")
    print_rich(f"  JSON: {json_path}")


# =============================================================================
# Main Test Runner
# =============================================================================

def run_test(scenario: Scenario, show_model: bool = True, show_hourly: bool = True, export_dir: str = None):
    """Run a complete test with the given scenario."""

    print_rich(f"\n[bold blue]{'='*60}[/bold blue]")
    print_rich(f"[bold blue]  KORA OPTIMIZER TEST[/bold blue]")
    print_rich(f"[bold blue]{'='*60}[/bold blue]\n")

    # Display scenario
    display_scenario_info(scenario)

    # Display model formulation
    if show_model:
        display_model_formulation(scenario)

    # Generate profiles
    print_rich("\n[bold]Generating input profiles...[/bold]")
    solar = generate_solar_profile(scenario)
    demand = generate_demand_profile(scenario)

    display_input_profiles(solar, demand)

    # Calculate baseline
    print_rich("\n[bold]Calculating baseline (fixed pricing, naive dispatch)...[/bold]")
    baseline = calculate_baseline(solar, demand, scenario)

    # Create optimizer inputs
    inputs = create_optimizer_inputs(scenario, solar, demand)

    # Run optimization
    print_rich(f"\n[bold]Running KORA optimizer (solver={scenario.solver})...[/bold]")

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Solving...", total=None)
            start = time.time()
            result = solve_kora_model(inputs, solver=scenario.solver, time_limit_sec=scenario.time_limit_sec)
            solve_time = time.time() - start
    else:
        start = time.time()
        result = solve_kora_model(inputs, solver=scenario.solver, time_limit_sec=scenario.time_limit_sec)
        solve_time = time.time() - start

    # Extract solution
    solution = extract_kora_solution(result)
    metrics = calculate_metrics(solution, inputs)

    # Display solver info
    display_solver_info(result, solve_time)

    # Display comparison
    print_rich("\n")
    display_comparison(baseline, metrics, scenario)

    # Display hourly results
    if show_hourly:
        print_rich("\n")
        display_hourly_results(solution, inputs, baseline)

    # Export if requested
    if export_dir:
        export_results(scenario, solar, demand, baseline, metrics, solution, export_dir)

    return baseline, metrics, solution


def interactive_mode():
    """Run in interactive mode with parameter adjustment."""
    if not RICH_AVAILABLE:
        print("Interactive mode requires 'rich' library. Install with: pip install rich")
        return

    console.print(Panel.fit(
        "[bold blue]KORA Optimizer Interactive Tester[/bold blue]\n\n"
        "Test the optimizer with different scenarios and parameters.\n"
        "See how changes in elasticity, pricing, weather affect results.",
        border_style="blue"
    ))

    while True:
        console.print("\n[bold]Available Scenarios:[/bold]")
        for i, (key, scen) in enumerate(SCENARIOS.items(), 1):
            console.print(f"  {i:2d}. [cyan]{key:<20}[/cyan] - {scen.description}")
        console.print(f"  {len(SCENARIOS)+1:2d}. [yellow]custom[/yellow]              - Create custom scenario")
        console.print(f"   0. [red]exit[/red]                 - Quit")

        choice = IntPrompt.ask("\nSelect scenario", default=1)

        if choice == 0:
            console.print("[dim]Goodbye![/dim]")
            break

        if choice == len(SCENARIOS) + 1:
            # Custom scenario
            scenario = create_custom_scenario()
        else:
            scenario_keys = list(SCENARIOS.keys())
            if 1 <= choice <= len(scenario_keys):
                scenario = SCENARIOS[scenario_keys[choice - 1]]
            else:
                console.print("[red]Invalid choice[/red]")
                continue

        # Ask for parameter overrides
        if Confirm.ask("Override parameters?", default=False):
            scenario = override_parameters(scenario)

        # Ask for display options
        show_model = Confirm.ask("Show model formulation?", default=True)
        show_hourly = Confirm.ask("Show hourly results?", default=True)
        export = Confirm.ask("Export results?", default=False)
        export_dir = Prompt.ask("Export directory", default="results/") if export else None

        # Run test
        run_test(scenario, show_model=show_model, show_hourly=show_hourly, export_dir=export_dir)

        console.print("\n" + "="*60)
        if not Confirm.ask("Run another test?", default=True):
            break

    console.print("[dim]Goodbye![/dim]")


def create_custom_scenario() -> Scenario:
    """Create a custom scenario interactively."""
    console.print("\n[bold]Create Custom Scenario[/bold]")

    name = Prompt.ask("Scenario name", default="Custom")
    description = Prompt.ask("Description", default="Custom test scenario")

    season = Prompt.ask("Season", choices=["dry", "wet"], default="dry")
    day_type = Prompt.ask("Day type", choices=["clear", "partly_cloudy", "cloudy", "intermittent"], default="clear")

    elasticity = FloatPrompt.ask("Demand elasticity (0-1)", default=0.6)
    price_min = FloatPrompt.ask("Min price (Ar/kWh)", default=1000.0)
    price_max = FloatPrompt.ask("Max price (Ar/kWh)", default=2500.0)

    demand_mult = FloatPrompt.ask("Demand multiplier", default=1.0)
    initial_soc = FloatPrompt.ask("Initial SOC (%)", default=30.0)

    return Scenario(
        name=name,
        description=description,
        season=season,
        day_type=day_type,
        elasticity=elasticity,
        price_min=price_min,
        price_max=price_max,
        demand_multiplier=demand_mult,
        initial_soc_pct=initial_soc,
    )


def override_parameters(scenario: Scenario) -> Scenario:
    """Override specific parameters of a scenario."""
    console.print("\n[dim]Press Enter to keep default value[/dim]")

    elasticity = FloatPrompt.ask(f"Elasticity [{scenario.elasticity}]", default=scenario.elasticity)
    price_min = FloatPrompt.ask(f"Min price [{scenario.price_min}]", default=scenario.price_min)
    price_max = FloatPrompt.ask(f"Max price [{scenario.price_max}]", default=scenario.price_max)
    demand_mult = FloatPrompt.ask(f"Demand multiplier [{scenario.demand_multiplier}]", default=scenario.demand_multiplier)
    initial_soc = FloatPrompt.ask(f"Initial SOC % [{scenario.initial_soc_pct}]", default=scenario.initial_soc_pct)

    # Create modified scenario
    return Scenario(
        name=scenario.name + " (modified)",
        description=scenario.description,
        season=scenario.season,
        day_type=scenario.day_type,
        pv_capacity_kw=scenario.pv_capacity_kw,
        peak_load_kw=scenario.peak_load_kw,
        demand_type=scenario.demand_type,
        demand_multiplier=demand_mult,
        battery_capacity_kwh=scenario.battery_capacity_kwh,
        battery_power_kw=scenario.battery_power_kw,
        initial_soc_pct=initial_soc,
        price_min=price_min,
        price_max=price_max,
        price_reference=scenario.price_reference,
        elasticity=elasticity,
        curtailment_penalty=scenario.curtailment_penalty,
        blackout_penalty=scenario.blackout_penalty,
        solver=scenario.solver,
        time_limit_sec=scenario.time_limit_sec,
    )


def run_all_scenarios(export_dir: str = None):
    """Run all predefined scenarios and summarize results."""
    if not RICH_AVAILABLE:
        print("This feature requires 'rich' library.")
        return

    console.print(Panel.fit(
        "[bold blue]Running All Scenarios[/bold blue]\n\n"
        f"Testing {len(SCENARIOS)} predefined scenarios...",
        border_style="blue"
    ))

    results = []

    for key, scenario in SCENARIOS.items():
        console.print(f"\n[bold]Running: {scenario.name}[/bold]")

        solar = generate_solar_profile(scenario)
        demand = generate_demand_profile(scenario)
        baseline = calculate_baseline(solar, demand, scenario)
        inputs = create_optimizer_inputs(scenario, solar, demand)

        start = time.time()
        result = solve_kora_model(inputs, solver=scenario.solver, time_limit_sec=30)
        solve_time = time.time() - start

        solution = extract_kora_solution(result)
        metrics = calculate_metrics(solution, inputs)

        results.append({
            "scenario": key,
            "name": scenario.name,
            "baseline_curtailment": baseline['curtailment_rate'],
            "optimized_curtailment": metrics['curtailment_rate'],
            "curtailment_reduction": (baseline['curtailment_rate'] - metrics['curtailment_rate']) / baseline['curtailment_rate'] * 100 if baseline['curtailment_rate'] > 0 else 0,
            "revenue_increase": (metrics['total_revenue_ariary'] - baseline['total_revenue_ariary']) / baseline['total_revenue_ariary'] * 100 if baseline['total_revenue_ariary'] > 0 else 0,
            "solve_time": solve_time,
        })

        console.print(f"  Curtailment: {baseline['curtailment_rate']*100:.1f}% → {metrics['curtailment_rate']*100:.1f}%")

    # Summary table
    console.print("\n")
    table = Table(title="All Scenarios Summary", box=box.ROUNDED)
    table.add_column("Scenario", style="cyan")
    table.add_column("Base Curt.", justify="right")
    table.add_column("Opt Curt.", justify="right", style="green")
    table.add_column("Reduction", justify="right")
    table.add_column("Rev. Increase", justify="right")
    table.add_column("Time (s)", justify="right", style="dim")

    for r in results:
        reduction_style = "green" if r['curtailment_reduction'] > 50 else ("yellow" if r['curtailment_reduction'] > 20 else "red")
        table.add_row(
            r['name'][:25],
            f"{r['baseline_curtailment']*100:.1f}%",
            f"{r['optimized_curtailment']*100:.1f}%",
            f"[{reduction_style}]{r['curtailment_reduction']:.0f}%[/{reduction_style}]",
            f"+{r['revenue_increase']:.0f}%",
            f"{r['solve_time']:.1f}",
        )

    console.print(table)

    if export_dir:
        json_path = Path(export_dir) / f"all_scenarios_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)
        console.print(f"\n[green]Summary exported to {json_path}[/green]")


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="KORA Optimizer Terminal Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python kora_tester.py                         # Interactive mode
    python kora_tester.py --scenario baseline     # Run specific scenario
    python kora_tester.py --scenario cloudy --elasticity 0.3
    python kora_tester.py --all                   # Run all scenarios
    python kora_tester.py --list                  # List available scenarios
    python kora_tester.py --export results/       # Export to directory

Available scenarios:
    baseline, cloudy, partly_cloudy, wet_season, weekend,
    high_demand, low_elasticity, high_elasticity, battery_degraded,
    narrow_price_band, wide_price_band, low_battery, full_battery,
    stress_test
        """
    )

    parser.add_argument("--scenario", "-s", type=str, help="Scenario to run")
    parser.add_argument("--all", "-a", action="store_true", help="Run all scenarios")
    parser.add_argument("--list", "-l", action="store_true", help="List available scenarios")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    # Parameter overrides
    parser.add_argument("--elasticity", "-e", type=float, help="Override demand elasticity")
    parser.add_argument("--price-min", type=float, help="Override minimum price")
    parser.add_argument("--price-max", type=float, help="Override maximum price")
    parser.add_argument("--demand-mult", type=float, help="Override demand multiplier")
    parser.add_argument("--initial-soc", type=float, help="Override initial SOC percent")
    parser.add_argument("--season", choices=["dry", "wet"], help="Override season")
    parser.add_argument("--day-type", choices=["clear", "partly_cloudy", "cloudy", "intermittent"], help="Override day type")

    # Display options
    parser.add_argument("--no-model", action="store_true", help="Hide model formulation")
    parser.add_argument("--no-hourly", action="store_true", help="Hide hourly results")
    parser.add_argument("--export", type=str, help="Export directory")

    # Solver options
    parser.add_argument("--solver", choices=["auto", "gurobi", "glpk", "highs"], default="auto", help="Solver to use")
    parser.add_argument("--time-limit", type=int, default=60, help="Solver time limit (seconds)")

    args = parser.parse_args()

    # List scenarios
    if args.list:
        print("\nAvailable Scenarios:")
        print("-" * 60)
        for key, scen in SCENARIOS.items():
            print(f"  {key:<20} - {scen.description}")
        print()
        return

    # Run all scenarios
    if args.all:
        run_all_scenarios(export_dir=args.export)
        return

    # Interactive mode
    if args.interactive or (not args.scenario and not args.all):
        interactive_mode()
        return

    # Run specific scenario
    if args.scenario:
        if args.scenario not in SCENARIOS:
            print(f"Error: Unknown scenario '{args.scenario}'")
            print(f"Available: {', '.join(SCENARIOS.keys())}")
            return

        scenario = SCENARIOS[args.scenario]

        # Apply overrides
        if args.elasticity is not None:
            scenario = Scenario(**{**scenario.__dict__, 'elasticity': args.elasticity})
        if args.price_min is not None:
            scenario = Scenario(**{**scenario.__dict__, 'price_min': args.price_min})
        if args.price_max is not None:
            scenario = Scenario(**{**scenario.__dict__, 'price_max': args.price_max})
        if args.demand_mult is not None:
            scenario = Scenario(**{**scenario.__dict__, 'demand_multiplier': args.demand_mult})
        if args.initial_soc is not None:
            scenario = Scenario(**{**scenario.__dict__, 'initial_soc_pct': args.initial_soc})
        if args.season:
            scenario = Scenario(**{**scenario.__dict__, 'season': args.season})
        if args.day_type:
            scenario = Scenario(**{**scenario.__dict__, 'day_type': args.day_type})
        if args.solver:
            scenario = Scenario(**{**scenario.__dict__, 'solver': args.solver})
        if args.time_limit:
            scenario = Scenario(**{**scenario.__dict__, 'time_limit_sec': args.time_limit})

        run_test(
            scenario,
            show_model=not args.no_model,
            show_hourly=not args.no_hourly,
            export_dir=args.export
        )


if __name__ == "__main__":
    main()