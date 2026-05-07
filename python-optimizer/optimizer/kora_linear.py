"""
KORA Linear Model - Works with GLPK!

This version uses DISCRETE price levels instead of continuous prices,
making the problem LINEAR (MILP) so it works with GLPK.

Key difference from kora_model.py:
- Instead of price[t] as a continuous variable, we choose from N fixed price levels
- Uses binary variables to select which price level
- Revenue calculation becomes linear: sum(price_level[i] * demand[i,t])
- Works with ANY linear solver (GLPK, CBC, HiGHS, etc.)

Still optimizes:
- Battery dispatch
- Dynamic pricing (just discretized)
- Demand response
- Curtailment minimization
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Optional
import numpy as np
import pyomo.environ as pyo


@dataclass
class KoraLinearInputs:
    """
    Inputs for linearized KORA model.
    Same as KoraOptimizerInputs but with discrete price levels.
    """
    # Time series forecasts
    pv_forecast_kw: List[float]
    base_demand_kw: List[float]

    # Battery parameters
    battery_capacity_kwh: float
    battery_power_kw: float
    soc_init_kwh: float
    soc_min_kwh: float
    soc_max_kwh: float
    eta_charge: float = 0.94
    eta_discharge: float = 0.94
    battery_cycle_cost_per_kwh: float = 0.01

    # Pricing parameters
    price_min: float = 1000  # Ariary/kWh
    price_max: float = 2500
    price_reference: float = 1750
    num_price_levels: int = 5  # Discretize into 5 price levels

    # Demand response
    demand_elasticity: float = 0.6

    # Penalties
    curtailment_value_per_kwh: float = 1500
    blackout_penalty_per_kwh: float = 5000

    # Grid (optional)
    grid_import_limit_kw: Optional[float] = None
    grid_export_limit_kw: Optional[float] = None
    wholesale_price_per_kwh: Optional[float] = None

    # Horizon
    timestep_hours: float = 1.0
    target_soc_end_kwh: Optional[float] = None


def build_kora_linear_model(inp: KoraLinearInputs) -> pyo.ConcreteModel:
    """
    Build linearized KORA model that works with GLPK.

    Key innovation: Discrete price levels instead of continuous prices.
    """
    m = pyo.ConcreteModel(name="kora_linear")

    T = range(len(inp.pv_forecast_kw))
    m.T = pyo.Set(initialize=T, ordered=True)

    dt = inp.timestep_hours

    # Create discrete price levels
    price_levels = np.linspace(inp.price_min, inp.price_max, inp.num_price_levels)
    m.PRICE_LEVELS = pyo.Set(initialize=range(inp.num_price_levels))

    # Parameters
    m.pv = pyo.Param(m.T, initialize={t: inp.pv_forecast_kw[t] for t in T})
    m.base_demand = pyo.Param(m.T, initialize={t: inp.base_demand_kw[t] for t in T})

    # ==========================================================================
    # DECISION VARIABLES
    # ==========================================================================

    # Battery variables (continuous)
    m.p_charge = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.battery_power_kw))
    m.p_discharge = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.battery_power_kw))
    m.soc = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(inp.soc_min_kwh, inp.soc_max_kwh))

    # Binary variables for charge/discharge exclusivity
    m.y_charge = pyo.Var(m.T, domain=pyo.Binary)
    m.y_discharge = pyo.Var(m.T, domain=pyo.Binary)

    # Price selection (BINARY - select one price level per timestep)
    m.price_select = pyo.Var(m.T, m.PRICE_LEVELS, domain=pyo.Binary)

    # Demand for each price level (continuous)
    m.demand = pyo.Var(m.T, m.PRICE_LEVELS, domain=pyo.NonNegativeReals)

    # Curtailment and unmet demand
    m.p_curtail = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, None))
    m.p_unmet = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, None))

    # Grid variables (if applicable)
    if inp.grid_import_limit_kw is not None:
        m.p_grid_import = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.grid_import_limit_kw))
    if inp.grid_export_limit_kw is not None:
        m.p_grid_export = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.grid_export_limit_kw))

    # ==========================================================================
    # CONSTRAINTS
    # ==========================================================================

    # Constraint: Select exactly one price level per timestep
    def one_price_rule(m, t):
        return sum(m.price_select[t, i] for i in m.PRICE_LEVELS) == 1
    m.one_price = pyo.Constraint(m.T, rule=one_price_rule)

    # Constraint: Demand response for each price level
    def demand_response_rule(m, t, i):
        price = price_levels[i]
        price_change = (price - inp.price_reference) / inp.price_reference
        demand_multiplier = 1 - inp.demand_elasticity * price_change
        demand_multiplier = max(0.5, min(2.0, demand_multiplier))  # Clamp

        # Demand[t,i] can only be non-zero if price_select[t,i] = 1
        # Use big-M: demand[t,i] <= M * price_select[t,i]
        max_demand = m.base_demand[t] * 2.0  # Big M
        return m.demand[t, i] <= max_demand * m.price_select[t, i]
    m.demand_bound = pyo.Constraint(m.T, m.PRICE_LEVELS, rule=demand_response_rule)

    # Constraint: Set demand value when price is selected
    def demand_value_rule(m, t, i):
        price = price_levels[i]
        price_change = (price - inp.price_reference) / inp.price_reference
        demand_multiplier = 1 - inp.demand_elasticity * price_change
        demand_multiplier = max(0.5, min(2.0, demand_multiplier))
        target_demand = m.base_demand[t] * demand_multiplier

        # When price_select[t,i] = 1, demand[t,i] should equal target_demand
        # When price_select[t,i] = 0, demand[t,i] should equal 0
        # This is: demand[t,i] = target_demand * price_select[t,i]
        return m.demand[t, i] == target_demand * m.price_select[t, i]
    m.demand_value = pyo.Constraint(m.T, m.PRICE_LEVELS, rule=demand_value_rule)

    # Total demand at time t
    def total_demand_rule(m, t):
        return sum(m.demand[t, i] for i in m.PRICE_LEVELS)
    m.total_demand = pyo.Expression(m.T, rule=total_demand_rule)

    # Battery SOC dynamics
    def soc_dynamics_rule(m, t):
        if t == 0:
            soc_prev = inp.soc_init_kwh
        else:
            soc_prev = m.soc[t-1]

        return m.soc[t] == soc_prev + dt * (inp.eta_charge * m.p_charge[t] - m.p_discharge[t] / inp.eta_discharge)
    m.soc_dynamics = pyo.Constraint(m.T, rule=soc_dynamics_rule)

    # Charge/discharge exclusivity (big-M)
    def charge_excl_rule(m, t):
        return m.p_charge[t] <= inp.battery_power_kw * m.y_charge[t]
    m.charge_excl = pyo.Constraint(m.T, rule=charge_excl_rule)

    def discharge_excl_rule(m, t):
        return m.p_discharge[t] <= inp.battery_power_kw * m.y_discharge[t]
    m.discharge_excl = pyo.Constraint(m.T, rule=discharge_excl_rule)

    def no_simult_rule(m, t):
        return m.y_charge[t] + m.y_discharge[t] <= 1
    m.no_simult = pyo.Constraint(m.T, rule=no_simult_rule)

    # Power balance
    def power_balance_rule(m, t):
        supply = m.pv[t] + m.p_discharge[t]
        consumption = m.total_demand[t] + m.p_charge[t]

        if inp.grid_import_limit_kw is not None:
            supply += m.p_grid_import[t]
        if inp.grid_export_limit_kw is not None:
            consumption += m.p_grid_export[t]

        return supply + m.p_unmet[t] == consumption + m.p_curtail[t]
    m.power_balance = pyo.Constraint(m.T, rule=power_balance_rule)

    # Curtailment limit
    def curtail_limit_rule(m, t):
        return m.p_curtail[t] <= m.pv[t]
    m.curtail_limit = pyo.Constraint(m.T, rule=curtail_limit_rule)

    # Final SOC target (optional)
    if inp.target_soc_end_kwh is not None:
        m.soc[T[-1]].fix(inp.target_soc_end_kwh)

    # ==========================================================================
    # OBJECTIVE: Minimize curtailment + blackouts - revenue + costs
    # ==========================================================================

    def objective_rule(m):
        # Revenue (LINEAR now!) = sum over all (t, price_level) of price * demand
        revenue = sum(
            price_levels[i] * m.demand[t, i] * dt
            for t in m.T
            for i in m.PRICE_LEVELS
        )

        # Curtailment cost
        curtailment_cost = sum(inp.curtailment_value_per_kwh * m.p_curtail[t] * dt for t in m.T)

        # Blackout cost
        blackout_cost = sum(inp.blackout_penalty_per_kwh * m.p_unmet[t] * dt for t in m.T)

        # Battery degradation
        cycle_cost = sum(inp.battery_cycle_cost_per_kwh * (m.p_charge[t] + m.p_discharge[t]) * dt for t in m.T)

        # Grid costs (if applicable)
        grid_cost = 0
        if inp.wholesale_price_per_kwh and inp.grid_import_limit_kw:
            grid_cost = sum(inp.wholesale_price_per_kwh * m.p_grid_import[t] * dt for t in m.T)

        # Minimize cost = curtailment + blackouts + cycles + grid - revenue
        return curtailment_cost + blackout_cost + cycle_cost + grid_cost - revenue

    m.obj = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

    return m


def solve_kora_linear(
    inp: KoraLinearInputs,
    solver: str = "glpk",
    time_limit_sec: int = 60
) -> pyo.ConcreteModel:
    """Solve the linearized KORA model."""

    model = build_kora_linear_model(inp)
    opt = pyo.SolverFactory(solver)

    # Set time limit
    if solver == "glpk":
        opt.options["tmlim"] = time_limit_sec
    elif solver in ["cbc", "gurobi"]:
        opt.options["seconds"] = time_limit_sec

    print(f"Solving linearized KORA with {solver}...")
    print(f"  Price levels: {inp.num_price_levels}")
    print(f"  Time steps: {len(inp.pv_forecast_kw)}")
    print(f"  Variables: ~{len(inp.pv_forecast_kw) * (inp.num_price_levels + 10)}")
    print()

    results = opt.solve(model, tee=True)

    if results.solver.status != pyo.SolverStatus.ok:
        raise RuntimeError(f"Solver failed: {results.solver.status}")

    return model


def extract_kora_linear_solution(model: pyo.ConcreteModel) -> Mapping[str, List[float]]:
    """Extract solution from linearized model."""

    # Get selected price at each timestep
    price_levels = np.linspace(
        model.component("pv").parent_component().parent_block().price_min,
        model.component("pv").parent_component().parent_block().price_max,
        len(model.PRICE_LEVELS)
    )

    def v(var):
        return [pyo.value(var[t]) for t in model.T]

    def selected_price(t):
        for i in model.PRICE_LEVELS:
            if pyo.value(model.price_select[t, i]) > 0.5:  # Binary is 1
                return price_levels[i]
        return price_levels[0]  # Fallback

    def total_demand(t):
        return sum(pyo.value(model.demand[t, i]) for i in model.PRICE_LEVELS)

    return {
        "p_charge_kw": v(model.p_charge),
        "p_discharge_kw": v(model.p_discharge),
        "soc_kwh": v(model.soc),
        "price_ariary": [selected_price(t) for t in model.T],
        "demand_kw": [total_demand(t) for t in model.T],
        "p_curtail_kw": v(model.p_curtail),
        "p_unmet_kw": v(model.p_unmet),
    }


if __name__ == "__main__":
    # Quick test
    print("Testing linearized KORA model...")

    from mahavelona_config import generate_madagascar_solar_profile, generate_madagascar_demand_profile

    solar = generate_madagascar_solar_profile(118.5, 24)
    demand = generate_madagascar_demand_profile(251, 53, 24)

    inputs = KoraLinearInputs(
        pv_forecast_kw=solar.tolist(),
        base_demand_kw=demand.tolist(),
        battery_capacity_kwh=115,
        battery_power_kw=54,
        soc_init_kwh=115 * 0.3,
        soc_min_kwh=115 * 0.2,
        soc_max_kwh=115 * 0.95,
        price_min=1000,
        price_max=2500,
        price_reference=1750,
        num_price_levels=5,
        demand_elasticity=0.6,
    )

    model = solve_kora_linear(inputs, solver="glpk")
    solution = extract_kora_linear_solution(model)

    print()
    print("✅ Linearized KORA works!")
    print(f"   Avg price: {np.mean(solution['price_ariary']):.0f} Ar/kWh")
    print(f"   Curtailment: {sum(solution['p_curtail_kw']):.1f} kWh")
