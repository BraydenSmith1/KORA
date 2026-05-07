"""
Example CLI to run the microgrid optimizer with synthetic data.

Usage:
    python run_optimizer.py
    python run_optimizer.py --hours 24 --solver highs
"""

import argparse
from pathlib import Path
from typing import List

import numpy as np

from optimizer.model import OptimizerInputs, extract_solution, solve_model


def default_scenario(hours: int):
    t = np.arange(hours)

    load = 8 + 2 * np.sin(2 * np.pi * t / 24 - 0.5)  # ~6-10 kW
    pv = np.clip(6 * np.sin(2 * np.pi * (t - 6) / 24), 0, None)  # midday PV

    price_buy = np.where((t % 24 >= 17) & (t % 24 < 22), 0.25, 0.12)
    price_sell = 0.06 * np.ones(hours)

    return load.tolist(), pv.tolist(), price_buy.tolist(), price_sell.tolist()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--hours", type=int, default=24, help="Number of timesteps (1h each)")
    p.add_argument("--solver", type=str, default="highs", help="Pyomo solver name (highs, glpk, cbc, etc.)")
    return p.parse_args()


def main():
    args = parse_args()

    load, pv, price_buy, price_sell = default_scenario(args.hours)

    inp = OptimizerInputs(
        load_kw=load,
        pv_kw=pv,
        price_buy=price_buy,
        price_sell=price_sell,
        battery_capacity_kwh=20,
        battery_power_kw=8,
        soc_init_kwh=10,
        soc_min_kwh=4,
        soc_max_kwh=20,
        eta_charge=0.94,
        eta_discharge=0.94,
        grid_import_limit_kw=15,
        grid_export_limit_kw=10,
        curtailment_penalty_per_kwh=0.02,
        shed_penalty_per_kwh=20.0,
        battery_cycle_cost_per_kwh=0.015,
        timestep_hours=1.0,
        target_soc_end_kwh=10,
    )

    model = solve_model(inp, solver=args.solver)
    sol = extract_solution(model)

    # Simple textual summary
    print("=== Objective cost ($) ===")
    print(f"{model.obj():.2f}")
    print("\n=== First 6 timesteps (kW / kWh) ===")
    for t in range(min(6, args.hours)):
        print(
            f"t={t:02d} "
            f"charge={sol['p_charge_kw'][t]:4.1f} "
            f"discharge={sol['p_discharge_kw'][t]:4.1f} "
            f"soc={sol['soc_kwh'][t]:5.1f} "
            f"import={sol['p_grid_import_kw'][t]:4.1f} "
            f"export={sol['p_grid_export_kw'][t]:4.1f} "
            f"curtail={sol['p_curtail_kw'][t]:4.1f} "
            f"shed={sol['p_shed_kw'][t]:4.1f}"
        )

    # Persist CSV for quick plotting
    out = Path("python-optimizer/output.csv")
    with out.open("w") as f:
        cols = [
            "t",
            "load_kw",
            "pv_kw",
            "p_charge_kw",
            "p_discharge_kw",
            "soc_kwh",
            "p_grid_import_kw",
            "p_grid_export_kw",
            "p_curtail_kw",
            "p_shed_kw",
            "price_buy",
            "price_sell",
        ]
        f.write(",".join(cols) + "\n")
        for t in range(args.hours):
            row = [
                t,
                load[t],
                pv[t],
                sol["p_charge_kw"][t],
                sol["p_discharge_kw"][t],
                sol["soc_kwh"][t],
                sol["p_grid_import_kw"][t],
                sol["p_grid_export_kw"][t],
                sol["p_curtail_kw"][t],
                sol["p_shed_kw"][t],
                price_buy[t],
                price_sell[t],
            ]
            f.write(",".join(f"{v:.4f}" if isinstance(v, float) else str(v) for v in row) + "\n")

    print(f"\nSaved time-series to {out}")
    print("Tip: import into a notebook or spreadsheet to visualize.")


if __name__ == "__main__":
    main()
