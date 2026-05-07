#!/usr/bin/env python
"""
Solver Availability Checker

Checks which optimization solvers are available on your system.
Run this to debug solver installation issues.

Usage:
    python check_solvers.py
"""

import sys
from pyomo.opt import SolverFactory
import pyomo.environ as pyo


def check_solver(name):
    """Check if a solver is available."""
    try:
        solver = SolverFactory(name)
        available = solver.available()
        executable = solver.executable() if hasattr(solver, 'executable') else "N/A"

        if available:
            return "✅ AVAILABLE", executable
        else:
            return "❌ NOT AVAILABLE", "Not found in PATH"
    except Exception as e:
        return "❌ ERROR", str(e)


def main():
    print("=" * 70)
    print("KORA Optimizer - Solver Availability Check")
    print("=" * 70)
    print()

    solvers_to_check = [
        ("highs", "HiGHS (recommended for production)"),
        ("glpk", "GLPK (good for development)"),
        ("cbc", "CBC (good alternative)"),
        ("appsi_highs", "APPSI HiGHS (Python interface, uses highspy)"),
        ("cplex", "CPLEX (commercial)"),
        ("gurobi", "Gurobi (commercial)"),
    ]

    available_solvers = []

    for solver_name, description in solvers_to_check:
        status, info = check_solver(solver_name)

        print(f"Solver: {solver_name}")
        print(f"  Description: {description}")
        print(f"  Status: {status}")
        if "AVAILABLE" in status:
            print(f"  Executable: {info}")
            available_solvers.append(solver_name)
        else:
            print(f"  Reason: {info}")
        print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if available_solvers:
        print(f"✅ Found {len(available_solvers)} available solver(s):")
        for solver in available_solvers:
            print(f"   - {solver}")
        print()
        print("You can use any of these solvers in your config files.")
        print()

        # Recommend best solver
        if "highs" in available_solvers:
            recommended = "highs"
        elif "appsi_highs" in available_solvers:
            recommended = "appsi_highs"
        elif "glpk" in available_solvers:
            recommended = "glpk"
        elif "cbc" in available_solvers:
            recommended = "cbc"
        else:
            recommended = available_solvers[0]

        print(f"🎯 Recommended: {recommended}")
        print()
        print("To use this solver, update your config:")
        print(f"   sites/mahavelona.yaml → optimizer.solver: \"{recommended}\"")

    else:
        print("❌ No solvers found!")
        print()
        print("ACTION REQUIRED:")
        print("1. Read SOLVER_SETUP.md for installation instructions")
        print("2. Install at least one solver:")
        print("   - conda install -c conda-forge glpk")
        print("   - OR brew install glpk (macOS)")
        print("   - OR conda install -c conda-forge highs")
        print("3. Run this script again to verify")
        sys.exit(1)

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
