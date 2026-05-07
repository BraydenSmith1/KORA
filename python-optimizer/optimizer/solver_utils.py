"""
Solver Detection and Fallback Utilities

Automatically detects available solvers and provides fallback options.
"""

from typing import List, Optional
from pyomo.opt import SolverFactory
import logging

logger = logging.getLogger(__name__)


def detect_available_solvers() -> List[str]:
    """
    Detect which optimization solvers are available on the system.

    Returns:
        List of available solver names, ordered by preference.
    """
    # Solvers to check, in order of preference
    # (fastest/best first, slowest/fallback last)
    candidates = [
        "highs",        # Fast, open-source, recommended
        "appsi_highs",  # Python interface to highspy (no binary needed)
        "cbc",          # Good open-source alternative
        "glpk",         # Slower but widely available
        "cplex",        # Commercial (if available)
        "gurobi",       # Commercial (if available)
    ]

    available = []

    for solver_name in candidates:
        try:
            solver = SolverFactory(solver_name)
            if solver.available():
                available.append(solver_name)
                logger.debug(f"Found available solver: {solver_name}")
        except Exception as e:
            logger.debug(f"Solver {solver_name} not available: {e}")

    return available


def get_best_solver(preferred: Optional[str] = None) -> str:
    """
    Get the best available solver.

    Args:
        preferred: Preferred solver name (will use if available)

    Returns:
        Name of the best available solver

    Raises:
        RuntimeError: If no solvers are available
    """
    available = detect_available_solvers()

    if not available:
        raise RuntimeError(
            "No optimization solvers found! Install one using:\n"
            "  conda install -c conda-forge glpk\n"
            "OR\n"
            "  conda install -c conda-forge highs\n"
            "See SOLVER_SETUP.md for details."
        )

    # If preferred solver is available, use it
    if preferred and preferred in available:
        logger.info(f"Using preferred solver: {preferred}")
        return preferred

    # Otherwise use the best available
    best = available[0]

    if preferred:
        logger.warning(
            f"Preferred solver '{preferred}' not available. "
            f"Falling back to '{best}'. "
            f"Available solvers: {', '.join(available)}"
        )
    else:
        logger.info(f"Auto-detected solver: {best}")

    return best


def get_solver_options(solver_name: str, time_limit_sec: int = 60) -> dict:
    """
    Get solver-specific options for time limits.

    Different solvers use different option names for time limits.

    Args:
        solver_name: Name of the solver
        time_limit_sec: Time limit in seconds

    Returns:
        Dictionary of solver options
    """
    options = {}

    if solver_name in ["highs", "appsi_highs"]:
        options["time_limit"] = time_limit_sec
    elif solver_name in ["cbc", "glpk"]:
        options["seconds"] = time_limit_sec
    elif solver_name == "gurobi":
        options["TimeLimit"] = time_limit_sec
    elif solver_name == "cplex":
        options["timelimit"] = time_limit_sec

    return options


if __name__ == "__main__":
    # Test script
    print("Detecting available solvers...")
    available = detect_available_solvers()

    if available:
        print(f"✅ Found {len(available)} solver(s):")
        for solver in available:
            print(f"   - {solver}")

        best = get_best_solver()
        print(f"\n🎯 Best available: {best}")
    else:
        print("❌ No solvers found!")
        print("Run: python check_solvers.py for more details")
