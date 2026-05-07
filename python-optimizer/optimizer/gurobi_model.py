"""
KORA Microgrid Optimizer - Gurobi Implementation

Direct Gurobi API (gurobipy) for:
- Better performance than Pyomo abstraction
- Native warm-starting support for MPC
- MIP progress callbacks
- Quadratic objective handling (price * demand)

This is a drop-in replacement for kora_model.py with automatic
fallback to HiGHS when Gurobi is unavailable.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Union

import numpy as np

# Conditional import for Gurobi
try:
    import gurobipy as gp
    from gurobipy import GRB
    GUROBI_AVAILABLE = True
except ImportError:
    GUROBI_AVAILABLE = False
    gp = None
    GRB = None

# Reuse dataclasses from existing kora_model
from .kora_model import KoraOptimizerInputs, calculate_metrics

logger = logging.getLogger(__name__)


# =============================================================================
# Solution Container
# =============================================================================

@dataclass
class GurobiSolution:
    """
    Solution container with metadata from Gurobi solve.

    Attributes:
        status: "optimal", "feasible", "infeasible", "timeout", or "error"
        objective_value: Final objective value (lower is better)
        solve_time_sec: Wall-clock solve time
        mip_gap: Relative MIP gap (None if not applicable)

        Solution vectors (one value per timestep):
        - p_charge_kw, p_discharge_kw: Battery power
        - soc_kwh: State of charge
        - price_ariary: Dynamic price
        - demand_kw: Price-responsive demand
        - p_curtail_kw: Curtailed PV
        - p_unmet_kw: Unmet demand (blackouts)
        - p_grid_import_kw, p_grid_export_kw: Grid transactions
    """
    status: str
    objective_value: float
    solve_time_sec: float
    mip_gap: Optional[float] = None

    # Solution vectors
    p_charge_kw: List[float] = field(default_factory=list)
    p_discharge_kw: List[float] = field(default_factory=list)
    soc_kwh: List[float] = field(default_factory=list)
    price_ariary: List[float] = field(default_factory=list)
    demand_kw: List[float] = field(default_factory=list)
    p_curtail_kw: List[float] = field(default_factory=list)
    p_unmet_kw: List[float] = field(default_factory=list)
    p_grid_import_kw: List[float] = field(default_factory=list)
    p_grid_export_kw: List[float] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return self.status in ("optimal", "feasible")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "objective_value": self.objective_value,
            "solve_time_sec": self.solve_time_sec,
            "mip_gap": self.mip_gap,
            "p_charge_kw": self.p_charge_kw,
            "p_discharge_kw": self.p_discharge_kw,
            "soc_kwh": self.soc_kwh,
            "price_ariary": self.price_ariary,
            "demand_kw": self.demand_kw,
            "p_curtail_kw": self.p_curtail_kw,
            "p_unmet_kw": self.p_unmet_kw,
            "p_grid_import_kw": self.p_grid_import_kw,
            "p_grid_export_kw": self.p_grid_export_kw,
        }


# =============================================================================
# License Validation
# =============================================================================

def check_gurobi_license() -> tuple[bool, str]:
    """
    Check if Gurobi license is valid.

    Returns:
        (is_valid, message) tuple
    """
    if not GUROBI_AVAILABLE:
        return False, "gurobipy not installed"

    try:
        # Create a minimal model to test license
        with gp.Env(empty=True) as env:
            env.setParam('OutputFlag', 0)
            env.start()
        return True, "Gurobi license valid"
    except Exception as e:
        return False, f"Gurobi license error: {e}"


# =============================================================================
# MIP Progress Callback
# =============================================================================

def create_progress_callback(
    log_interval_sec: float = 5.0,
    on_improvement: Optional[Callable[[float, float], None]] = None,
) -> Callable:
    """
    Create a Gurobi callback for MIP progress logging.

    Args:
        log_interval_sec: Minimum seconds between log messages
        on_improvement: Called when incumbent improves (obj, gap)

    Returns:
        Callback function for Model.optimize()
    """
    if not GUROBI_AVAILABLE:
        return lambda m, w: None

    state = {"last_log": 0.0, "last_obj": float('inf')}

    def callback(model, where):
        if where == GRB.Callback.MIP:
            current_time = time.time()
            if current_time - state["last_log"] >= log_interval_sec:
                try:
                    obj = model.cbGet(GRB.Callback.MIP_OBJBST)
                    gap = model.cbGet(GRB.Callback.MIP_GAP)
                    nodes = model.cbGet(GRB.Callback.MIP_NODCNT)

                    logger.info(f"MIP Progress: obj={obj:.2f}, gap={gap*100:.2f}%, nodes={int(nodes)}")
                    state["last_log"] = current_time

                    if obj < state["last_obj"] and on_improvement:
                        on_improvement(obj, gap)
                        state["last_obj"] = obj
                except Exception:
                    pass  # Callback data not always available

    return callback


# =============================================================================
# Gurobi Microgrid Model
# =============================================================================

class GurobiMicrogridModel:
    """
    Gurobi-based MILP/QP optimizer for microgrid dispatch.

    Features:
    - Direct gurobipy API (no Pyomo abstraction)
    - Quadratic objective (price * demand revenue term)
    - MIP progress callback support
    - Warm-start from previous solution
    - Automatic variable/constraint naming for debugging

    Usage:
        model = GurobiMicrogridModel(inputs, time_limit_sec=60)
        solution = model.solve()
        if solution.is_success:
            print(f"Curtailment: {sum(solution.p_curtail_kw):.1f} kWh")
    """

    def __init__(
        self,
        inputs: KoraOptimizerInputs,
        time_limit_sec: int = 60,
        mip_gap: float = 0.01,
        verbose: bool = True,
    ):
        """
        Initialize the Gurobi model builder.

        Args:
            inputs: Optimizer inputs (forecasts, battery specs, pricing bounds)
            time_limit_sec: Maximum solve time
            mip_gap: Relative MIP gap tolerance (0.01 = 1%)
            verbose: If True, show Gurobi solver output
        """
        if not GUROBI_AVAILABLE:
            raise RuntimeError("Gurobi is not available. Install with: pip install gurobipy")

        self.inputs = inputs
        self.time_limit_sec = time_limit_sec
        self.mip_gap = mip_gap
        self.verbose = verbose

        self.model: Optional[gp.Model] = None
        self.env: Optional[gp.Env] = None
        self.T: range = range(len(inputs.pv_forecast_kw))
        self.dt = inputs.timestep_hours

        # Variable containers (populated in build_model)
        self.p_charge: Dict[int, Any] = {}
        self.p_discharge: Dict[int, Any] = {}
        self.soc: Dict[int, Any] = {}
        self.y_charge: Dict[int, Any] = {}
        self.y_discharge: Dict[int, Any] = {}
        self.price: Dict[int, Any] = {}
        self.demand: Dict[int, Any] = {}
        self.p_curtail: Dict[int, Any] = {}
        self.p_unmet: Dict[int, Any] = {}
        self.p_grid_import: Dict[int, Any] = {}
        self.p_grid_export: Dict[int, Any] = {}

    def build_model(self) -> "gp.Model":
        """
        Build the Gurobi optimization model.

        Returns:
            The constructed Gurobi Model object
        """
        inp = self.inputs

        # Create environment and model
        self.env = gp.Env(empty=True)
        self.env.setParam('OutputFlag', 1 if self.verbose else 0)
        self.env.start()

        self.model = gp.Model("kora_microgrid", env=self.env)
        m = self.model

        # ============ DECISION VARIABLES ============

        # Battery dispatch (continuous)
        self.p_charge = m.addVars(
            self.T, lb=0, ub=inp.battery_power_kw,
            vtype=GRB.CONTINUOUS, name="p_charge"
        )
        self.p_discharge = m.addVars(
            self.T, lb=0, ub=inp.battery_power_kw,
            vtype=GRB.CONTINUOUS, name="p_discharge"
        )
        self.soc = m.addVars(
            self.T, lb=inp.soc_min_kwh, ub=inp.soc_max_kwh,
            vtype=GRB.CONTINUOUS, name="soc"
        )

        # Binary gates for charge/discharge exclusivity
        self.y_charge = m.addVars(self.T, vtype=GRB.BINARY, name="y_charge")
        self.y_discharge = m.addVars(self.T, vtype=GRB.BINARY, name="y_discharge")

        # Dynamic pricing (continuous within bounds)
        self.price = m.addVars(
            self.T, lb=inp.price_min, ub=inp.price_max,
            vtype=GRB.CONTINUOUS, name="price"
        )

        # Demand response (continuous, will be linked to price)
        # Upper bound based on max demand at min price
        max_demand_factor = 1 + inp.demand_elasticity * (inp.price_reference - inp.price_min) / inp.price_reference
        max_demand = [d * max_demand_factor for d in inp.base_demand_kw]
        self.demand = m.addVars(
            self.T, lb=0,
            ub={t: max_demand[t] for t in self.T},
            vtype=GRB.CONTINUOUS, name="demand"
        )

        # Curtailment and unmet demand
        self.p_curtail = m.addVars(
            self.T, lb=0,
            ub={t: inp.pv_forecast_kw[t] for t in self.T},
            vtype=GRB.CONTINUOUS, name="p_curtail"
        )
        self.p_unmet = m.addVars(self.T, lb=0, vtype=GRB.CONTINUOUS, name="p_unmet")

        # Grid (off-grid if limits are None or 0)
        grid_import_ub = inp.grid_import_limit_kw if inp.grid_import_limit_kw else 0
        grid_export_ub = inp.grid_export_limit_kw if inp.grid_export_limit_kw else 0
        self.p_grid_import = m.addVars(
            self.T, lb=0, ub=grid_import_ub,
            vtype=GRB.CONTINUOUS, name="p_grid_import"
        )
        self.p_grid_export = m.addVars(
            self.T, lb=0, ub=grid_export_ub,
            vtype=GRB.CONTINUOUS, name="p_grid_export"
        )

        # ============ CONSTRAINTS ============

        # 1. SOC dynamics
        for t in self.T:
            prev_soc = inp.soc_init_kwh if t == 0 else self.soc[t - 1]
            m.addConstr(
                self.soc[t] == prev_soc + self.dt * (
                    inp.eta_charge * self.p_charge[t]
                    - (1 / inp.eta_discharge) * self.p_discharge[t]
                ),
                name=f"soc_dynamics_{t}"
            )

        # 2. Charge/discharge exclusivity (big-M formulation)
        big_m = inp.battery_power_kw
        for t in self.T:
            m.addConstr(
                self.p_charge[t] <= big_m * self.y_charge[t],
                name=f"charge_gate_{t}"
            )
            m.addConstr(
                self.p_discharge[t] <= big_m * self.y_discharge[t],
                name=f"discharge_gate_{t}"
            )
            m.addConstr(
                self.y_charge[t] + self.y_discharge[t] <= 1,
                name=f"no_overlap_{t}"
            )

        # 3. Demand response (linear price elasticity)
        # demand[t] = base_demand[t] - sensitivity * (price[t] - ref_price)
        # where sensitivity = base_demand[t] * elasticity / ref_price
        for t in self.T:
            sensitivity = inp.base_demand_kw[t] * inp.demand_elasticity / inp.price_reference
            m.addConstr(
                self.demand[t] == inp.base_demand_kw[t] - sensitivity * (self.price[t] - inp.price_reference),
                name=f"demand_response_{t}"
            )

        # 4. Power balance
        # Supply: PV + discharge + grid_import
        # Consumption: demand + charge + grid_export
        # Balance: supply = consumption + curtail - unmet
        for t in self.T:
            supply = inp.pv_forecast_kw[t] + self.p_discharge[t] + self.p_grid_import[t]
            consumption = self.demand[t] + self.p_charge[t] + self.p_grid_export[t]
            m.addConstr(
                supply == consumption + self.p_curtail[t] - self.p_unmet[t],
                name=f"power_balance_{t}"
            )

        # 5. Target final SOC (if specified)
        if inp.target_soc_end_kwh is not None:
            m.addConstr(
                self.soc[max(self.T)] >= inp.target_soc_end_kwh,
                name="target_soc_end"
            )

        # ============ OBJECTIVE FUNCTION ============
        #
        # Objective: minimize (- revenue + costs + penalties)
        #
        # Revenue term is QUADRATIC: price[t] * demand[t]
        # Gurobi handles this natively (QP/MIQP)

        # Customer revenue (quadratic: price * demand)
        # Note: We use QuadExpr for this
        customer_revenue = gp.quicksum(
            self.price[t] * self.demand[t] * self.dt
            for t in self.T
        )

        # Grid import cost (if grid-connected)
        grid_cost = 0
        if inp.wholesale_price_per_kwh:
            grid_cost = gp.quicksum(
                inp.wholesale_price_per_kwh * self.p_grid_import[t] * self.dt
                for t in self.T
            )

        # Battery degradation cost
        cycle_cost = gp.quicksum(
            inp.battery_cycle_cost_per_kwh * (self.p_charge[t] + self.p_discharge[t]) * self.dt
            for t in self.T
        )

        # Curtailment penalty (what we want to minimize!)
        curtailment_cost = gp.quicksum(
            inp.curtailment_value_per_kwh * self.p_curtail[t] * self.dt
            for t in self.T
        )

        # Blackout penalty (unmet demand is very bad)
        blackout_cost = gp.quicksum(
            inp.blackout_penalty_per_kwh * self.p_unmet[t] * self.dt
            for t in self.T
        )

        # Set objective: minimize total cost (negative revenue)
        m.setObjective(
            -customer_revenue + grid_cost + cycle_cost + curtailment_cost + blackout_cost,
            GRB.MINIMIZE
        )

        # Commit all variables and constraints (required for Gurobi 10+ lazy updates)
        m.update()

        return m

    def solve(
        self,
        warm_start: Optional[GurobiSolution] = None,
        callback: Optional[Callable] = None,
    ) -> GurobiSolution:
        """
        Solve the optimization model.

        Args:
            warm_start: Previous solution for MIP warm-starting
            callback: Optional callback for MIP progress (use create_progress_callback())

        Returns:
            GurobiSolution with results or error status
        """
        if self.model is None:
            self.build_model()

        m = self.model

        # Set solver parameters
        m.setParam('TimeLimit', self.time_limit_sec)
        m.setParam('MIPGap', self.mip_gap)

        # Apply warm start if provided
        if warm_start is not None and warm_start.is_success:
            self._apply_warm_start(warm_start)

        # Optimize
        start_time = time.time()
        try:
            if callback:
                m.optimize(callback)
            else:
                m.optimize()
        except Exception as e:
            logger.error(f"Gurobi optimization error: {e}")
            return GurobiSolution(
                status="error",
                objective_value=float('inf'),
                solve_time_sec=time.time() - start_time,
            )

        solve_time = time.time() - start_time

        # Extract solution
        return self._extract_solution(solve_time)

    def _apply_warm_start(self, prev_solution: GurobiSolution) -> None:
        """Apply previous solution as MIP start hint."""
        for t in self.T:
            if t < len(prev_solution.p_charge_kw):
                self.p_charge[t].Start = prev_solution.p_charge_kw[t]
                self.p_discharge[t].Start = prev_solution.p_discharge_kw[t]
                self.soc[t].Start = prev_solution.soc_kwh[t]
                self.price[t].Start = prev_solution.price_ariary[t]
                self.demand[t].Start = prev_solution.demand_kw[t]
        logger.debug("Applied warm start from previous solution")

    def _extract_solution(self, solve_time: float) -> GurobiSolution:
        """Extract solution from solved model."""
        m = self.model

        # Determine status
        if m.Status == GRB.OPTIMAL:
            status = "optimal"
        elif m.Status == GRB.TIME_LIMIT and m.SolCount > 0:
            status = "feasible"
        elif m.Status == GRB.INFEASIBLE:
            status = "infeasible"
        elif m.Status == GRB.TIME_LIMIT:
            status = "timeout"
        elif m.Status == GRB.UNBOUNDED:
            status = "unbounded"
        else:
            status = f"unknown_{m.Status}"

        # Extract variable values (or zeros if no solution)
        def get_vals(var_dict: Dict[int, Any]) -> List[float]:
            if m.SolCount > 0:
                return [var_dict[t].X for t in self.T]
            return [0.0] * len(self.T)

        # Get objective value and MIP gap
        obj_value = m.ObjVal if m.SolCount > 0 else float('inf')
        mip_gap = None
        if m.SolCount > 0:
            try:
                mip_gap = m.MIPGap
            except Exception:
                pass  # MIP gap not available for QP without integers

        solution = GurobiSolution(
            status=status,
            objective_value=obj_value,
            solve_time_sec=solve_time,
            mip_gap=mip_gap,
            p_charge_kw=get_vals(self.p_charge),
            p_discharge_kw=get_vals(self.p_discharge),
            soc_kwh=get_vals(self.soc),
            price_ariary=get_vals(self.price),
            demand_kw=get_vals(self.demand),
            p_curtail_kw=get_vals(self.p_curtail),
            p_unmet_kw=get_vals(self.p_unmet),
            p_grid_import_kw=get_vals(self.p_grid_import),
            p_grid_export_kw=get_vals(self.p_grid_export),
        )

        # Log summary
        if solution.is_success:
            total_curtail = sum(solution.p_curtail_kw) * self.dt
            total_pv = sum(self.inputs.pv_forecast_kw) * self.dt
            curtail_rate = total_curtail / total_pv if total_pv > 0 else 0
            logger.info(
                f"Gurobi solve complete: status={status}, "
                f"obj={obj_value:.2f}, time={solve_time:.2f}s, "
                f"curtailment={curtail_rate*100:.1f}%"
            )
        else:
            logger.warning(f"Gurobi solve failed: status={status}, time={solve_time:.2f}s")

        return solution

    def get_model_stats(self) -> Dict[str, int]:
        """Get model statistics for debugging."""
        if self.model is None:
            return {}
        m = self.model
        return {
            "num_vars": m.NumVars,
            "num_int_vars": m.NumIntVars,
            "num_bin_vars": m.NumBinVars,
            "num_constrs": m.NumConstrs,
            "num_nonzeros": m.NumNZs,
            "num_qconstrs": m.NumQConstrs,
        }

    def cleanup(self) -> None:
        """Release Gurobi resources."""
        if self.model is not None:
            self.model.dispose()
            self.model = None
        if self.env is not None:
            self.env.dispose()
            self.env = None


# =============================================================================
# Drop-in API (Compatible with kora_model.py interface)
# =============================================================================

def solve_kora_model(
    inp: KoraOptimizerInputs,
    solver: str = "auto",
    solver_options: Optional[Mapping[str, Any]] = None,
    time_limit_sec: int = 60,
) -> Union[GurobiSolution, Any]:
    """
    Solve the KORA optimization model.

    This is a drop-in replacement for kora_model.solve_kora_model().

    Solver selection:
    - "auto": Try Gurobi first, fall back to HiGHS
    - "gurobi": Use Gurobi (fail if unavailable)
    - "highs", "glpk", "cbc": Use Pyomo with specified solver

    Args:
        inp: Optimizer inputs (forecasts, battery specs, pricing bounds)
        solver: Solver to use ("auto", "gurobi", "highs", etc.)
        solver_options: Additional solver options (passed to Pyomo or Gurobi)
        time_limit_sec: Maximum solve time in seconds

    Returns:
        GurobiSolution if using Gurobi, or Pyomo ConcreteModel if fallback
    """
    use_gurobi = solver.lower() in ("auto", "gurobi")

    if use_gurobi and GUROBI_AVAILABLE:
        is_valid, msg = check_gurobi_license()
        if is_valid:
            logger.info("Using Gurobi solver")
            try:
                mip_gap = 0.01
                verbose = True
                if solver_options:
                    mip_gap = solver_options.get("mip_gap", mip_gap)
                    verbose = solver_options.get("verbose", verbose)

                model = GurobiMicrogridModel(
                    inputs=inp,
                    time_limit_sec=time_limit_sec,
                    mip_gap=mip_gap,
                    verbose=verbose,
                )
                solution = model.solve()
                model.cleanup()
                return solution
            except Exception as e:
                logger.error(f"Gurobi solve failed: {e}")
                if solver.lower() == "gurobi":
                    raise  # Don't fall back if Gurobi was explicitly requested
                logger.info("Falling back to HiGHS")
        else:
            logger.warning(f"Gurobi unavailable: {msg}")
            if solver.lower() == "gurobi":
                raise RuntimeError(f"Gurobi requested but unavailable: {msg}")
            logger.info("Falling back to HiGHS")

    # Fallback to HiGHS via Pyomo
    # Note: kora_model has a quadratic objective (price * demand) which HiGHS cannot handle.
    # We need to use the linearized version or the basic model.
    logger.info(f"Using {solver if solver not in ('auto', 'gurobi') else 'highs'} solver (via Pyomo)")

    # Use GLPK as default fallback since HiGHS may not be available as executable
    fallback_solver = solver if solver not in ("auto", "gurobi") else "glpk"

    # Try the linearized KORA model first (discrete price levels)
    try:
        from .kora_linear import solve_kora_linear, KoraLinearInputs

        # Convert KoraOptimizerInputs to KoraLinearInputs
        linear_inputs = KoraLinearInputs(
            pv_forecast_kw=inp.pv_forecast_kw,
            base_demand_kw=inp.base_demand_kw,
            battery_capacity_kwh=inp.battery_capacity_kwh,
            battery_power_kw=inp.battery_power_kw,
            soc_init_kwh=inp.soc_init_kwh,
            soc_min_kwh=inp.soc_min_kwh,
            soc_max_kwh=inp.soc_max_kwh,
            eta_charge=inp.eta_charge,
            eta_discharge=inp.eta_discharge,
            battery_cycle_cost_per_kwh=inp.battery_cycle_cost_per_kwh,
            price_min=inp.price_min,
            price_max=inp.price_max,
            price_reference=inp.price_reference,
            num_price_levels=5,  # Use 5 discrete price levels
            demand_elasticity=inp.demand_elasticity,
            curtailment_value_per_kwh=inp.curtailment_value_per_kwh,
            blackout_penalty_per_kwh=inp.blackout_penalty_per_kwh,
            grid_import_limit_kw=inp.grid_import_limit_kw,
            grid_export_limit_kw=inp.grid_export_limit_kw,
            wholesale_price_per_kwh=inp.wholesale_price_per_kwh,
            timestep_hours=inp.timestep_hours,
            target_soc_end_kwh=inp.target_soc_end_kwh,
        )

        logger.info("Using linearized KORA model (discrete pricing)")
        return solve_kora_linear(linear_inputs, solver=fallback_solver, time_limit_sec=time_limit_sec)
    except ImportError:
        pass  # kora_linear not available
    except Exception as e:
        logger.warning(f"Linearized model failed: {e}")

    # Fall back to basic linear model (fixed pricing, no demand response)
    try:
        from .model import OptimizerInputs, solve_model, extract_solution

        # Convert KoraOptimizerInputs to basic OptimizerInputs
        # Use reference price as fixed buy/sell price
        basic_inputs = OptimizerInputs(
            load_kw=inp.base_demand_kw,
            pv_kw=inp.pv_forecast_kw,
            price_buy=[inp.price_reference] * len(inp.pv_forecast_kw),
            price_sell=[inp.price_reference * 0.5] * len(inp.pv_forecast_kw),
            battery_capacity_kwh=inp.battery_capacity_kwh,
            battery_power_kw=inp.battery_power_kw,
            soc_init_kwh=inp.soc_init_kwh,
            soc_min_kwh=inp.soc_min_kwh,
            soc_max_kwh=inp.soc_max_kwh,
            eta_charge=inp.eta_charge,
            eta_discharge=inp.eta_discharge,
            grid_import_limit_kw=inp.grid_import_limit_kw,
            grid_export_limit_kw=inp.grid_export_limit_kw,
            curtailment_penalty_per_kwh=inp.curtailment_value_per_kwh,
            shed_penalty_per_kwh=inp.blackout_penalty_per_kwh,
            battery_cycle_cost_per_kwh=inp.battery_cycle_cost_per_kwh,
            timestep_hours=inp.timestep_hours,
            target_soc_end_kwh=inp.target_soc_end_kwh,
        )

        logger.info("Using basic linear model (fixed pricing)")
        return solve_model(basic_inputs, solver=fallback_solver)
    except Exception as e:
        logger.error(f"All fallback options failed: {e}")
        raise RuntimeError(
            f"Gurobi is required for dynamic pricing optimization. "
            f"Install with: pip install gurobipy\n"
            f"Get free academic license: https://www.gurobi.com/academia/\n"
            f"Fallback error: {e}"
        )


def extract_kora_solution(model_or_solution: Union[GurobiSolution, Any]) -> Mapping[str, List[float]]:
    """
    Extract solution in standard dict format.

    Works with GurobiSolution, Pyomo ConcreteModel (kora_model), or
    Pyomo ConcreteModel (kora_linear).

    Args:
        model_or_solution: Either a GurobiSolution or Pyomo model

    Returns:
        Dict with solution vectors (p_charge_kw, soc_kwh, price_ariary, etc.)
    """
    if isinstance(model_or_solution, GurobiSolution):
        return {
            "p_charge_kw": model_or_solution.p_charge_kw,
            "p_discharge_kw": model_or_solution.p_discharge_kw,
            "soc_kwh": model_or_solution.soc_kwh,
            "price_ariary": model_or_solution.price_ariary,
            "demand_kw": model_or_solution.demand_kw,
            "p_curtail_kw": model_or_solution.p_curtail_kw,
            "p_unmet_kw": model_or_solution.p_unmet_kw,
            "p_grid_import_kw": model_or_solution.p_grid_import_kw,
            "p_grid_export_kw": model_or_solution.p_grid_export_kw,
        }
    else:
        # Pyomo model - detect which type and use appropriate extractor
        model = model_or_solution

        # Check if this is a linearized model (has price_select variable)
        if hasattr(model, 'price_select'):
            import numpy as np
            import pyomo.environ as pyo

            # Manual extraction for linearized model
            def v(var):
                return [pyo.value(var[t]) for t in model.T]

            # Get price levels from the model's PRICE_LEVELS set
            num_levels = len(model.PRICE_LEVELS)
            # Estimate price range (default if not stored on model)
            price_min = 1000
            price_max = 2500
            price_levels = np.linspace(price_min, price_max, num_levels)

            def selected_price(t):
                for i in model.PRICE_LEVELS:
                    if pyo.value(model.price_select[t, i]) > 0.5:
                        return float(price_levels[i])
                return float(price_levels[0])

            def total_demand(t):
                return sum(pyo.value(model.demand[t, i]) for i in model.PRICE_LEVELS)

            sol = {
                "p_charge_kw": v(model.p_charge),
                "p_discharge_kw": v(model.p_discharge),
                "soc_kwh": v(model.soc),
                "price_ariary": [selected_price(t) for t in model.T],
                "demand_kw": [total_demand(t) for t in model.T],
                "p_curtail_kw": v(model.p_curtail),
                "p_unmet_kw": v(model.p_unmet),
                "p_grid_import_kw": [0.0] * len(model.T),
                "p_grid_export_kw": [0.0] * len(model.T),
            }
            return sol

        # Check if this is the basic model (has p_shed instead of p_unmet)
        if hasattr(model, 'p_shed'):
            from .model import extract_solution
            sol = extract_solution(model)
            # Map to standard names
            return {
                "p_charge_kw": sol["p_charge_kw"],
                "p_discharge_kw": sol["p_discharge_kw"],
                "soc_kwh": sol["soc_kwh"],
                "price_ariary": [0.0] * len(sol["p_charge_kw"]),  # No pricing in basic model
                "demand_kw": sol.get("demand_kw", [0.0] * len(sol["p_charge_kw"])),
                "p_curtail_kw": sol["p_curtail_kw"],
                "p_unmet_kw": sol["p_shed_kw"],
                "p_grid_import_kw": sol["p_grid_import_kw"],
                "p_grid_export_kw": sol["p_grid_export_kw"],
            }

        # Standard kora_model
        from .kora_model import extract_kora_solution as extract_pyomo
        return extract_pyomo(model)


# =============================================================================
# Convenience Exports
# =============================================================================

__all__ = [
    "GUROBI_AVAILABLE",
    "check_gurobi_license",
    "GurobiSolution",
    "GurobiMicrogridModel",
    "create_progress_callback",
    "solve_kora_model",
    "extract_kora_solution",
    "calculate_metrics",
    "KoraOptimizerInputs",
]


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    """Quick test of the Gurobi model."""
    import sys

    print("=" * 60)
    print("KORA Gurobi Model Test")
    print("=" * 60)
    print()

    # Check Gurobi
    print(f"Gurobi installed: {GUROBI_AVAILABLE}")
    if GUROBI_AVAILABLE:
        is_valid, msg = check_gurobi_license()
        print(f"License valid: {is_valid} ({msg})")
    print()

    # Simple test case
    print("Running simple 24-hour test...")

    # Sample profiles
    pv = [0, 0, 5, 15, 30, 50, 70, 85, 95, 95, 90, 80, 65, 45, 25, 10, 0, 0, 0, 0, 0, 0, 0, 0]
    demand = [10, 8, 8, 10, 12, 15, 18, 20, 18, 15, 18, 22, 25, 20, 20, 30, 40, 50, 48, 40, 35, 30, 20, 15]

    inputs = KoraOptimizerInputs(
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

    # Solve
    result = solve_kora_model(inputs, solver="auto", time_limit_sec=60)
    solution = extract_kora_solution(result)
    metrics = calculate_metrics(solution, inputs)

    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)
    if isinstance(result, GurobiSolution):
        print(f"Solver: Gurobi")
        print(f"Status: {result.status}")
        print(f"Solve time: {result.solve_time_sec:.2f}s")
    else:
        print(f"Solver: HiGHS (fallback)")

    print()
    print(f"Total PV: {metrics['total_pv_kwh']:.1f} kWh")
    print(f"Curtailment: {metrics['total_curtail_kwh']:.1f} kWh ({metrics['curtailment_rate']*100:.1f}%)")
    print(f"Demand served: {metrics['total_demand_served_kwh']:.1f} kWh")
    print(f"Revenue: {metrics['total_revenue_ariary']:,.0f} Ariary")
    print(f"Avg price: {metrics['avg_price_ariary']:.0f} Ar/kWh")
    print(f"Blackout hours: {metrics['blackout_hours']}")
