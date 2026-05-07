"""
Pyomo-based microgrid optimization model.

Decision variables (per time step t):
  - p_charge[t] (kW)    : battery charge power
  - p_discharge[t] (kW) : battery discharge power
  - soc[t] (kWh)        : battery state of charge
  - p_grid_import[t]    : power bought from grid
  - p_grid_export[t]    : power sold to grid
  - p_curtail[t]        : curtailed PV/renewable generation
  - p_shed[t]           : load shed (unserved load)
  - y_charge[t], y_discharge[t] (binary) prevent simultaneous charge/discharge

Constraints:
  - SOC bounds and dynamics
  - Power limits (battery, grid import/export)
  - Charge/discharge exclusivity using big-M
  - Power balance (generation + imports + discharge = load + charge + export + curtailment balance + shed)
  - Optional initial/final SOC targets

Objective:
  Minimize net operating cost:
    purchase_cost - export_revenue
    + curtailment_penalty + shed_penalty + battery_degradation_cost

This stays linear/MILP so it runs with free solvers (HiGHS, CBC, GLPK).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional

import pyomo.environ as pyo


@dataclass
class OptimizerInputs:
    # Time series (one value per timestep)
    load_kw: List[float]
    pv_kw: List[float]
    price_buy: List[float]   # $/kWh import tariff
    price_sell: List[float]  # $/kWh export tariff (feed-in)

    # Battery parameters
    battery_capacity_kwh: float
    battery_power_kw: float
    soc_init_kwh: float
    soc_min_kwh: float
    soc_max_kwh: float
    eta_charge: float = 0.95
    eta_discharge: float = 0.95

    # Grid limits
    grid_import_limit_kw: Optional[float] = None
    grid_export_limit_kw: Optional[float] = None

    # Penalties / costs
    curtailment_penalty_per_kwh: float = 0.02  # soft incentive to use renewables
    shed_penalty_per_kwh: float = 10.0         # large to avoid unserved load
    battery_cycle_cost_per_kwh: float = 0.01   # degradation proxy

    # Horizon settings
    timestep_hours: float = 1.0
    target_soc_end_kwh: Optional[float] = None


def build_model(inp: OptimizerInputs) -> pyo.ConcreteModel:
    """Create a Pyomo model for the microgrid dispatch problem."""

    m = pyo.ConcreteModel(name="microgrid_milp")

    T = range(len(inp.load_kw))
    m.T = pyo.Set(initialize=T, ordered=True)

    big_m = inp.battery_power_kw

    # Decision variables
    m.p_charge = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.battery_power_kw))
    m.p_discharge = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(0, inp.battery_power_kw))
    m.soc = pyo.Var(m.T, domain=pyo.NonNegativeReals, bounds=(inp.soc_min_kwh, inp.soc_max_kwh))
    m.p_grid_import = pyo.Var(m.T, domain=pyo.NonNegativeReals)
    m.p_grid_export = pyo.Var(m.T, domain=pyo.NonNegativeReals)
    m.p_curtail = pyo.Var(m.T, domain=pyo.NonNegativeReals)
    m.p_shed = pyo.Var(m.T, domain=pyo.NonNegativeReals)

    # Binary vars to prevent simultaneous charge/discharge
    m.y_charge = pyo.Var(m.T, domain=pyo.Binary)
    m.y_discharge = pyo.Var(m.T, domain=pyo.Binary)

    # Parameters as Pyomo Param objects for cleaner expressions
    m.load = pyo.Param(m.T, initialize={t: inp.load_kw[t] for t in T})
    m.pv = pyo.Param(m.T, initialize={t: inp.pv_kw[t] for t in T})
    m.price_buy = pyo.Param(m.T, initialize={t: inp.price_buy[t] for t in T})
    m.price_sell = pyo.Param(m.T, initialize={t: inp.price_sell[t] for t in T})

    dt = inp.timestep_hours

    # Constraints
    def soc_dynamics(m, t):
        prev_soc = inp.soc_init_kwh if t == 0 else m.soc[t - 1]
        return m.soc[t] == prev_soc + dt * (
            inp.eta_charge * m.p_charge[t] - (1 / inp.eta_discharge) * m.p_discharge[t]
        )

    m.soc_balance = pyo.Constraint(m.T, rule=soc_dynamics)

    if inp.grid_import_limit_kw is not None:
        m.grid_import_limit = pyo.Constraint(m.T, rule=lambda m, t: m.p_grid_import[t] <= inp.grid_import_limit_kw)

    if inp.grid_export_limit_kw is not None:
        m.grid_export_limit = pyo.Constraint(m.T, rule=lambda m, t: m.p_grid_export[t] <= inp.grid_export_limit_kw)

    # Prevent simultaneous charge/discharge via big-M formulation
    m.charge_gate = pyo.Constraint(m.T, rule=lambda m, t: m.p_charge[t] <= big_m * m.y_charge[t])
    m.discharge_gate = pyo.Constraint(m.T, rule=lambda m, t: m.p_discharge[t] <= big_m * m.y_discharge[t])
    m.no_overlap = pyo.Constraint(m.T, rule=lambda m, t: m.y_charge[t] + m.y_discharge[t] <= 1)

    # Power balance at each timestep
    def power_balance(m, t):
        return (
            m.pv[t]
            + m.p_grid_import[t]
            + m.p_discharge[t]
            - m.p_curtail[t]
            == m.load[t] - m.p_shed[t] + m.p_charge[t] + m.p_grid_export[t]
        )

    m.balance = pyo.Constraint(m.T, rule=power_balance)

    # Target final SOC if requested
    if inp.target_soc_end_kwh is not None:
        m.target_soc = pyo.Constraint(expr=m.soc[max(T)] >= inp.target_soc_end_kwh)

    # Objective
    def objective_rule(m):
        purchase = sum(dt * m.p_grid_import[t] * m.price_buy[t] for t in m.T)
        export_rev = sum(dt * m.p_grid_export[t] * m.price_sell[t] for t in m.T)
        curtail_pen = sum(dt * inp.curtailment_penalty_per_kwh * m.p_curtail[t] for t in m.T)
        shed_pen = sum(dt * inp.shed_penalty_per_kwh * m.p_shed[t] for t in m.T)
        cycle_cost = sum(
            dt * inp.battery_cycle_cost_per_kwh * (m.p_charge[t] + m.p_discharge[t]) for t in m.T
        )
        return purchase - export_rev + curtail_pen + shed_pen + cycle_cost

    m.obj = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

    return m


def solve_model(
    inp: OptimizerInputs,
    solver: str = "highs",
    solver_options: Optional[Mapping[str, float]] = None,
) -> pyo.ConcreteModel:
    """Build and solve the model, returning the populated Pyomo model."""

    model = build_model(inp)
    opt = pyo.SolverFactory(solver)
    if solver_options:
        for k, v in solver_options.items():
            opt.options[k] = v

    results = opt.solve(model, tee=False)
    if (results.solver.status != pyo.SolverStatus.ok) or (results.solver.termination_condition not in {pyo.TerminationCondition.optimal, pyo.TerminationCondition.feasible}):
        raise RuntimeError(f"Solver failed: {results.solver.status}, {results.solver.termination_condition}")

    return model


def extract_solution(model: pyo.ConcreteModel) -> Mapping[str, List[float]]:
    """Return solution time series as plain Python lists."""
    def v(var):
        return [pyo.value(var[t]) for t in model.T]

    return {
        "p_charge_kw": v(model.p_charge),
        "p_discharge_kw": v(model.p_discharge),
        "soc_kwh": v(model.soc),
        "p_grid_import_kw": v(model.p_grid_import),
        "p_grid_export_kw": v(model.p_grid_export),
        "p_curtail_kw": v(model.p_curtail),
        "p_shed_kw": v(model.p_shed),
    }

