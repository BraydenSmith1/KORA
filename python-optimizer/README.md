# Microgrid Optimization Engine (Pyomo)

This folder contains a minimal but complete MILP optimizer that dispatches a battery + PV + grid interconnection to minimize cost / maximize operator profit subject to physical and tariff constraints.

## What it solves
- Decision variables: battery charge/discharge power, SOC, grid import/export, curtailment, load shedding, optional binary gates to avoid simultaneous charge/discharge.
- Constraints: SOC bounds/dynamics, power limits, grid import/export caps, power balance each timestep, optional final SOC target.
- Objective: minimize net cost = energy purchases – export revenue + penalties for curtailment & shed + battery degradation proxy.

## Quick start
```bash
cd python-optimizer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_optimizer.py --hours 24 --solver highs
```

Outputs:
- Console summary of objective and first few timesteps.
- `python-optimizer/output.csv` with full time-series for plotting.

## Modbus collector (RTDS/RSCAD)
- File: `python-optimizer/modbus_collector.py`
- Config: copy `modbus_config.example.json` to `modbus_config.json` and adjust host/port/register map.
- Run:
```bash
cd python-optimizer
source .venv/bin/activate  # if already created
pip install -r requirements.txt
python modbus_collector.py --config python-optimizer/modbus_config.json
```
- Behavior: polls Modbus TCP registers on a short interval, scales values, and POSTs JSON to your Node ingest endpoint (`api_url`). Add an API token in config if needed.
- Tip: keep reader (polling) and writer (setpoints) separate; this collector only reads.

## Solver options
- Default solver: `highs` (fast open-source). Install via `pip install highs` if not already available in your environment. Pyomo also works with `glpk`, `cbc`, `cplex`, `gurobi`, etc. Use `--solver glpk` if that’s what you have.
- If no solver is installed, install `highspy` (`pip install highspy`) or `pip install pulp` and call `--solver cbc` when CBC is on PATH.

## Integrating with your Node backend
- Treat this as a micro-service: wrap `solve_model` in a FastAPI/Flask endpoint that accepts JSON (forecasts, tariffs, limits) and returns dispatch setpoints.
- The core API surface you need:
  - Build inputs: `optimizer.model.OptimizerInputs(...)`
  - Solve: `solve_model(inputs, solver="highs")`
  - Get arrays: `extract_solution(model)`
- Since the rest of your repo is JS/TS, you can containerize this directory and call it over HTTP/GRPC from `api/src/server.js`.

## Tweaking the model
- Penalties: adjust `curtailment_penalty_per_kwh`, `shed_penalty_per_kwh`, `battery_cycle_cost_per_kwh`.
- Tariffs: pass time-varying `price_buy` / `price_sell`.
- Limits: set `grid_import_limit_kw` / `grid_export_limit_kw`; change battery power/energy and efficiencies.
- Horizon: change `--hours` and `timestep_hours` (keep consistent with your data resolution).
- Target SOC: set `target_soc_end_kwh` to ensure readiness for next day.

## Roadmap ideas
- Add diesel or other generators with fuel cost and min up/down constraints.
- Include demand charges or tiered tariffs.
- Run in MPC mode: re-solve every 15 minutes with updated forecasts.
- Add scenario-based stochastic runs for uncertain PV/load forecasts.
