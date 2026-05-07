"""
KORA Microgrid Optimizer - Enhanced Model

This optimizer solves for:
1. Battery dispatch (charge/discharge schedule)
2. Dynamic pricing (optimal $/kWh per hour to minimize curtailment)
3. Demand response (how customers respond to price signals)

Primary objective: MINIMIZE CURTAILMENT (Kora's mission!)
Secondary objective: MAXIMIZE OPERATOR PROFIT
Constraint: Keep prices affordable for customers

Key innovation: Price is a DECISION VARIABLE, not an input.
The optimizer determines the optimal price that balances:
- Lower price → More customers buy → Less curtailment
- Higher price → More revenue per kWh → Better profit

This is what makes Kora special!
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Optional

import pyomo.environ as pyo
import numpy as np

from .solver_utils import get_best_solver, get_solver_options


@dataclass
class KoraOptimizerInputs:
    """
    Enhanced inputs for the KORA optimizer.

    Key difference from basic optimizer:
    - price_buy/price_sell are BOUNDS (min/max allowed), not fixed values
    - We add demand_elasticity to model customer price response
    - We add curtailment_value to quantify the cost of waste
    """

    # Time series forecasts (one value per timestep)
    pv_forecast_kw: List[float]  # Expected solar production
    base_demand_kw: List[float]  # Baseline demand (at reference price)

    # Battery parameters
    battery_capacity_kwh: float
    battery_power_kw: float  # Max charge/discharge rate
    soc_init_kwh: float
    soc_min_kwh: float
    soc_max_kwh: float
    eta_charge: float = 0.94
    eta_discharge: float = 0.94
    battery_cycle_cost_per_kwh: float = 0.01  # Degradation cost

    # Pricing parameters (CRITICAL FOR KORA!)
    price_min: float = 1000  # Minimum allowed price (Ariary/kWh) - affordability floor
    price_max: float = 2500  # Maximum allowed price (Ariary/kWh) - regulatory cap
    price_reference: float = 1750  # Reference price (baseline, what customers expect)

    # Demand response parameters
    demand_elasticity: float = 0.6  # How responsive customers are to price
    # elasticity = 0.6 means: 10% price drop → 6% demand increase

    # Value parameters (economics)
    curtailment_value_per_kwh: float = 1500  # What curtailed energy is "worth" (lost opportunity)
    # This should be ~= avg selling price, since curtailed kWh = lost revenue
    blackout_penalty_per_kwh: float = 5000  # Penalty for unmet demand (VERY BAD!)

    # Grid limits (if grid-connected; set to None for off-grid)
    grid_import_limit_kw: Optional[float] = None
    grid_export_limit_kw: Optional[float] = None
    wholesale_price_per_kwh: Optional[float] = None  # Cost to buy from grid

    # Horizon settings
    timestep_hours: float = 1.0
    target_soc_end_kwh: Optional[float] = None  # Desired final battery SOC


def build_kora_model(inp: KoraOptimizerInputs) -> pyo.ConcreteModel:
    """
    Build the KORA optimization model.

    Decision variables:
    1. p_charge[t], p_discharge[t] - Battery power (kW)
    2. soc[t] - Battery state of charge (kWh)
    3. price[t] - Price to charge customers (Ariary/kWh) ← THIS IS THE KEY!
    4. demand[t] - Actual demand (responds to price)
    5. p_curtail[t] - Curtailed PV (what we want to minimize!)
    6. p_unmet[t] - Unmet demand (blackouts)

    The optimizer finds the price schedule that minimizes curtailment
    while keeping the operator profitable.
    """

    m = pyo.ConcreteModel(name="kora_optimizer")

    T = range(len(inp.pv_forecast_kw))
    m.T = pyo.Set(initialize=T, ordered=True)

    dt = inp.timestep_hours
    big_m = inp.battery_power_kw

    # ============ DECISION VARIABLES ============

    # Battery dispatch
    m.p_charge = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.battery_power_kw))
    m.p_discharge = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.battery_power_kw))
    m.soc = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(inp.soc_min_kwh, inp.soc_max_kwh))

    # Binary gates (prevent simultaneous charge/discharge)
    m.y_charge = pyo.Var(m.T, domain=pyo.Binary)
    m.y_discharge = pyo.Var(m.T, domain=pyo.Binary)

    # PRICING (this is what makes KORA special!)
    m.price = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(inp.price_min, inp.price_max))

    # Demand (responds to price via elasticity)
    m.demand = pyo.Var(m.T, domain=pyo.NonNegativeReals)

    # Curtailment and unmet demand
    m.p_curtail = pyo.Var(m.T, domain=pyo.NonNegativeReals)
    m.p_unmet = pyo.Var(m.T, domain=pyo.NonNegativeReals)  # Blackouts (should be zero!)

    # Grid import/export (if grid-connected)
    if inp.grid_import_limit_kw is not None:
        m.p_grid_import = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.grid_import_limit_kw))
    else:
        m.p_grid_import = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, 0))  # Off-grid

    if inp.grid_export_limit_kw is not None:
        m.p_grid_export = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.grid_export_limit_kw))
    else:
        m.p_grid_export = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, 0))  # Off-grid

    # ============ PARAMETERS (forecasts) ============
    m.pv = pyo.Param(m.T, initialize={t: inp.pv_forecast_kw[t] for t in T})
    m.base_demand = pyo.Param(m.T, initialize={t: inp.base_demand_kw[t] for t in T})

    # ============ CONSTRAINTS ============

    # 1. Battery SOC dynamics
    def soc_dynamics(m, t):
        prev_soc = inp.soc_init_kwh if t == 0 else m.soc[t - 1]
        return m.soc[t] == prev_soc + dt * (
            inp.eta_charge * m.p_charge[t] - (1 / inp.eta_discharge) * m.p_discharge[t]
        )

    m.soc_balance = pyo.Constraint(m.T, rule=soc_dynamics)

    # 2. Prevent simultaneous charge/discharge (big-M)
    m.charge_gate = pyo.Constraint(m.T, rule=lambda m, t: m.p_charge[t] <= big_m * m.y_charge[t])
    m.discharge_gate = pyo.Constraint(m.T, rule=lambda m, t: m.p_discharge[t] <= big_m * m.y_discharge[t])
    m.no_overlap = pyo.Constraint(m.T, rule=lambda m, t: m.y_charge[t] + m.y_discharge[t] <= 1)

    # 3. Demand response (price elasticity)
    # demand[t] = base_demand[t] × (1 - elasticity × (price[t] - ref_price) / ref_price)
    # This is NON-LINEAR, so we linearize it using a piecewise approximation
    #
    # Simplified linear approximation for MILP:
    # demand[t] = base_demand[t] - sensitivity × (price[t] - ref_price)
    # where sensitivity = base_demand[t] × elasticity / ref_price

    def demand_response(m, t):
        sensitivity = m.base_demand[t] * inp.demand_elasticity / inp.price_reference
        return m.demand[t] == m.base_demand[t] - sensitivity * (m.price[t] - inp.price_reference)

    m.demand_link = pyo.Constraint(m.T, rule=demand_response)

    # 4. Power balance (supply = demand)
    # Supply: PV + battery discharge + grid import
    # Demand: customer demand + battery charge + grid export + curtailment
    # Unmet: if supply < demand, p_unmet > 0 (blackout)

    def power_balance(m, t):
        supply = m.pv[t] + m.p_discharge[t] + m.p_grid_import[t]
        consumption = m.demand[t] + m.p_charge[t] + m.p_grid_export[t]
        return supply == consumption + m.p_curtail[t] - m.p_unmet[t]

    m.balance = pyo.Constraint(m.T, rule=power_balance)

    # 5. Curtailment bounds (can't curtail more than available PV)
    m.curtail_limit = pyo.Constraint(m.T, rule=lambda m, t: m.p_curtail[t] <= m.pv[t])

    # 6. Target final SOC (if specified)
    if inp.target_soc_end_kwh is not None:
        m.target_soc = pyo.Constraint(expr=m.soc[max(T)] >= inp.target_soc_end_kwh)

    # ============ OBJECTIVE FUNCTION ============

    def objective_rule(m):
        """
        KORA's multi-objective function:

        Primary goal: MINIMIZE CURTAILMENT (reduce waste!)
        Secondary goal: MAXIMIZE REVENUE (keep operator profitable)
        Tertiary goal: AVOID BLACKOUTS (unmet demand is very bad)

        We use weighted penalties to balance these goals.
        """

        # Revenue from customers
        # revenue = sum over t of: price[t] × demand[t] × dt
        customer_revenue = sum(m.price[t] * m.demand[t] * dt for t in m.T)

        # Cost of grid imports (if grid-connected)
        if inp.wholesale_price_per_kwh is not None:
            grid_cost = sum(inp.wholesale_price_per_kwh * m.p_grid_import[t] * dt for t in m.T)
        else:
            grid_cost = 0

        # Battery degradation cost
        cycle_cost = sum(inp.battery_cycle_cost_per_kwh * (m.p_charge[t] + m.p_discharge[t]) * dt for t in m.T)

        # CURTAILMENT PENALTY (this is what we want to minimize!)
        # Treat each curtailed kWh as lost revenue
        curtailment_cost = sum(inp.curtailment_value_per_kwh * m.p_curtail[t] * dt for t in m.T)

        # BLACKOUT PENALTY (unmet demand is extremely bad!)
        blackout_cost = sum(inp.blackout_penalty_per_kwh * m.p_unmet[t] * dt for t in m.T)

        # Total objective: MAXIMIZE profit - curtailment cost - blackout cost
        # In Pyomo minimize form:
        return (
            -customer_revenue  # Negative because we're minimizing (want to maximize revenue)
            + grid_cost
            + cycle_cost
            + curtailment_cost  # Penalty for waste
            + blackout_cost     # Big penalty for blackouts
        )

    m.obj = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

    return m


def solve_kora_model(
    inp: KoraOptimizerInputs,
    solver: str = "highs",
    solver_options: Optional[Mapping[str, float]] = None,
    time_limit_sec: int = 60
) -> pyo.ConcreteModel:
    """Build and solve the KORA model, returning the populated Pyomo model."""

    model = build_kora_model(inp)

    # Auto-detect best solver if preferred solver isn't available
    actual_solver = get_best_solver(preferred=solver)

    opt = pyo.SolverFactory(actual_solver)

    # Set solver-specific time limit options
    solver_opts = get_solver_options(actual_solver, time_limit_sec)
    for k, v in solver_opts.items():
        opt.options[k] = v

    # Apply any user-provided options
    if solver_options:
        for k, v in solver_options.items():
            opt.options[k] = v

    print(f"Solving KORA optimization with {actual_solver}...")
    results = opt.solve(model, tee=True)  # tee=True shows solver output

    if results.solver.status != pyo.SolverStatus.ok:
        raise RuntimeError(f"Solver failed: {results.solver.status}")

    if results.solver.termination_condition not in {
        pyo.TerminationCondition.optimal,
        pyo.TerminationCondition.feasible
    }:
        print(f"Warning: Solver terminated with condition: {results.solver.termination_condition}")

    return model


def extract_kora_solution(model: pyo.ConcreteModel) -> Mapping[str, List[float]]:
    """Extract solution time series as plain Python lists."""

    def v(var):
        return [pyo.value(var[t]) for t in model.T]

    return {
        "p_charge_kw": v(model.p_charge),
        "p_discharge_kw": v(model.p_discharge),
        "soc_kwh": v(model.soc),
        "price_ariary": v(model.price),
        "demand_kw": v(model.demand),
        "p_curtail_kw": v(model.p_curtail),
        "p_unmet_kw": v(model.p_unmet),
        "p_grid_import_kw": v(model.p_grid_import) if hasattr(model, 'p_grid_import') else [0] * len(model.T),
        "p_grid_export_kw": v(model.p_grid_export) if hasattr(model, 'p_grid_export') else [0] * len(model.T),
    }


def calculate_metrics(solution: Mapping[str, List[float]], inputs: KoraOptimizerInputs) -> dict:
    """Calculate summary metrics from the solution."""

    dt = inputs.timestep_hours

    # Energy metrics
    total_pv = sum(inputs.pv_forecast_kw) * dt
    total_curtail = sum(solution["p_curtail_kw"]) * dt
    total_demand_served = sum(solution["demand_kw"]) * dt
    total_unmet = sum(solution["p_unmet_kw"]) * dt

    curtailment_rate = total_curtail / total_pv if total_pv > 0 else 0

    # Revenue metrics (Ariary)
    total_revenue = sum(
        solution["price_ariary"][t] * solution["demand_kw"][t] * dt
        for t in range(len(solution["price_ariary"]))
    )

    avg_price = total_revenue / total_demand_served if total_demand_served > 0 else 0

    # Battery metrics
    battery_energy_cycled = sum(solution["p_charge_kw"]) * dt  # kWh charged
    battery_cycles = battery_energy_cycled / inputs.battery_capacity_kwh if inputs.battery_capacity_kwh > 0 else 0

    return {
        "total_pv_kwh": total_pv,
        "total_curtail_kwh": total_curtail,
        "curtailment_rate": curtailment_rate,
        "total_demand_served_kwh": total_demand_served,
        "total_unmet_kwh": total_unmet,
        "total_revenue_ariary": total_revenue,
        "avg_price_ariary": avg_price,
        "battery_cycles": battery_cycles,
        "blackout_hours": sum(1 for u in solution["p_unmet_kw"] if u > 0.1),
    }


if __name__ == "__main__":
    """Test the KORA optimizer with sample data"""
    import numpy as np

    # Simple test case
    hours = 24

    # Sample solar profile (peak at noon)
    pv = [0, 0, 5, 15, 30, 50, 70, 85, 95, 95, 90, 80, 65, 45, 25, 10, 0, 0, 0, 0, 0, 0, 0, 0]

    # Sample demand profile (peak in evening)
    demand = [10, 8, 8, 10, 12, 15, 18, 20, 18, 15, 18, 22, 25, 20, 20, 30, 40, 50, 48, 40, 35, 30, 20, 15]

    inp = KoraOptimizerInputs(
        pv_forecast_kw=pv,
        base_demand_kw=demand,
        battery_capacity_kwh=100,
        battery_power_kw=50,
        soc_init_kwh=50,
        soc_min_kwh=20,
        soc_max_kwh=95,
        price_min=1000,
        price_max=2500,
        price_reference=1750,
        demand_elasticity=0.6,
        curtailment_value_per_kwh=1500,
        blackout_penalty_per_kwh=5000,
    )

    model = solve_kora_model(inp, solver="highs")
    solution = extract_kora_solution(model)
    metrics = calculate_metrics(solution, inp)

    print("\n=== KORA Solution ===")
    print(f"Total PV: {metrics['total_pv_kwh']:.1f} kWh")
    print(f"Curtailment: {metrics['total_curtail_kwh']:.1f} kWh ({metrics['curtailment_rate']*100:.1f}%)")
    print(f"Demand served: {metrics['total_demand_served_kwh']:.1f} kWh")
    print(f"Revenue: {metrics['total_revenue_ariary']:.0f} Ar")
    print(f"Avg price: {metrics['avg_price_ariary']:.0f} Ar/kWh")
    print(f"Blackout hours: {metrics['blackout_hours']}")

    print("\nSample hours:")
    for t in [6, 10, 14, 18, 20]:
        print(
            f"  {t:02d}:00 - "
            f"PV: {pv[t]:5.1f} kW, "
            f"Price: {solution['price_ariary'][t]:4.0f} Ar, "
            f"Demand: {solution['demand_kw'][t]:5.1f} kW, "
            f"Charge: {solution['p_charge_kw'][t]:5.1f} kW, "
            f"Discharge: {solution['p_discharge_kw'][t]:5.1f} kW, "
            f"Curtail: {solution['p_curtail_kw'][t]:5.1f} kW"
        )
