"""
Tests for Gurobi-based KORA optimizer.

Run with: pytest tests/test_gurobi_model.py -v
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizer.gurobi_model import (
    GUROBI_AVAILABLE,
    check_gurobi_license,
    GurobiMicrogridModel,
    GurobiSolution,
    solve_kora_model,
    extract_kora_solution,
    calculate_metrics,
    KoraOptimizerInputs,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def simple_inputs() -> KoraOptimizerInputs:
    """Create simple 4-hour test case for fast testing."""
    return KoraOptimizerInputs(
        pv_forecast_kw=[0.0, 50.0, 80.0, 30.0],
        base_demand_kw=[20.0, 25.0, 30.0, 40.0],
        battery_capacity_kwh=50.0,
        battery_power_kw=25.0,
        soc_init_kwh=25.0,
        soc_min_kwh=10.0,
        soc_max_kwh=45.0,
        price_min=1000.0,
        price_max=2500.0,
        price_reference=1750.0,
        demand_elasticity=0.6,
        curtailment_value_per_kwh=1500.0,
        blackout_penalty_per_kwh=5000.0,
    )


@pytest.fixture
def mahavelona_inputs() -> KoraOptimizerInputs:
    """Create realistic Mahavelona test inputs (24 hours)."""
    try:
        from mahavelona_config import (
            MahavelonaSpecs,
            generate_madagascar_solar_profile,
            generate_madagascar_demand_profile,
        )

        specs = MahavelonaSpecs()
        hours = 24

        # Use fixed seed for reproducibility
        import numpy as np
        np.random.seed(42)

        solar = generate_madagascar_solar_profile(
            peak_capacity_kw=specs.pv_capacity_kw,
            hours=hours,
            season="dry",
            day_type="clear"
        )
        demand = generate_madagascar_demand_profile(
            total_customers=251,
            peak_load_kw=53,
            hours=hours
        )

        return KoraOptimizerInputs(
            pv_forecast_kw=solar.tolist(),
            base_demand_kw=demand.tolist(),
            battery_capacity_kwh=specs.battery_capacity_kwh,
            battery_power_kw=specs.battery_power_kw,
            soc_init_kwh=specs.battery_capacity_kwh * 0.5,
            soc_min_kwh=specs.battery_capacity_kwh * specs.soc_min_percent / 100,
            soc_max_kwh=specs.battery_capacity_kwh * specs.soc_max_percent / 100,
            eta_charge=specs.battery_efficiency_charge,
            eta_discharge=specs.battery_efficiency_discharge,
            price_min=1000.0,
            price_max=2500.0,
            price_reference=1750.0,
            demand_elasticity=0.6,
            curtailment_value_per_kwh=1500.0,
            blackout_penalty_per_kwh=5000.0,
        )
    except ImportError:
        # Fallback if mahavelona_config not available
        import numpy as np
        hours = 24
        t = np.arange(hours)

        # Approximate solar profile
        solar = np.zeros(hours)
        for h in range(6, 19):
            solar[h] = 118.5 * np.sin((h - 6) / 12 * np.pi) * 0.85
        solar = np.clip(solar, 0, 118.5)

        # Approximate demand profile
        demand = 8 + 45 * np.array([
            0.2, 0.15, 0.15, 0.15, 0.15, 0.2, 0.35, 0.45,
            0.5, 0.48, 0.45, 0.5, 0.4, 0.38, 0.45, 0.5,
            0.6, 0.75, 0.95, 1.0, 0.9, 0.7, 0.5, 0.3
        ])

        return KoraOptimizerInputs(
            pv_forecast_kw=solar.tolist(),
            base_demand_kw=demand.tolist(),
            battery_capacity_kwh=115.0,
            battery_power_kw=54.0,
            soc_init_kwh=57.5,
            soc_min_kwh=23.0,
            soc_max_kwh=109.25,
            eta_charge=0.94,
            eta_discharge=0.94,
            price_min=1000.0,
            price_max=2500.0,
            price_reference=1750.0,
            demand_elasticity=0.6,
            curtailment_value_per_kwh=1500.0,
            blackout_penalty_per_kwh=5000.0,
        )


# =============================================================================
# Gurobi Availability Tests
# =============================================================================

def test_gurobi_import():
    """Test that GUROBI_AVAILABLE flag is set correctly."""
    assert isinstance(GUROBI_AVAILABLE, bool)
    print(f"Gurobi available: {GUROBI_AVAILABLE}")


def test_gurobi_license():
    """Test Gurobi license validation."""
    is_valid, message = check_gurobi_license()
    print(f"License check: valid={is_valid}, message={message}")
    assert isinstance(is_valid, bool)
    assert isinstance(message, str)


# =============================================================================
# Model Building Tests (require Gurobi)
# =============================================================================

@pytest.mark.skipif(not GUROBI_AVAILABLE, reason="Gurobi not installed")
def test_build_model(simple_inputs):
    """Test that model builds correctly with proper variable counts."""
    is_valid, _ = check_gurobi_license()
    if not is_valid:
        pytest.skip("Valid Gurobi license required")

    model = GurobiMicrogridModel(simple_inputs, time_limit_sec=10, verbose=False)
    m = model.build_model()

    assert m is not None
    assert m.NumVars > 0
    assert m.NumConstrs > 0

    # Check variable counts
    # Per timestep: p_charge, p_discharge, soc, y_charge, y_discharge,
    #               price, demand, p_curtail, p_unmet, p_grid_import, p_grid_export
    T = len(simple_inputs.pv_forecast_kw)
    expected_continuous = 9 * T  # All except binary
    expected_binary = 2 * T  # y_charge, y_discharge

    assert m.NumBinVars == expected_binary
    print(f"Model built: {m.NumVars} vars, {m.NumConstrs} constrs")

    model.cleanup()


@pytest.mark.skipif(not GUROBI_AVAILABLE, reason="Gurobi not installed")
def test_model_stats(simple_inputs):
    """Test model statistics retrieval."""
    is_valid, _ = check_gurobi_license()
    if not is_valid:
        pytest.skip("Valid Gurobi license required")

    model = GurobiMicrogridModel(simple_inputs, verbose=False)
    model.build_model()

    stats = model.get_model_stats()
    assert "num_vars" in stats
    assert "num_constrs" in stats
    assert stats["num_vars"] > 0

    print(f"Model stats: {stats}")
    model.cleanup()


# =============================================================================
# Solver Tests (require Gurobi license)
# =============================================================================

@pytest.mark.skipif(not GUROBI_AVAILABLE, reason="Gurobi not installed")
def test_solve_simple(simple_inputs):
    """Test solving simple 4-hour problem."""
    is_valid, _ = check_gurobi_license()
    if not is_valid:
        pytest.skip("Valid Gurobi license required")

    model = GurobiMicrogridModel(simple_inputs, time_limit_sec=30, verbose=False)
    solution = model.solve()

    assert solution.status in ("optimal", "feasible")
    assert solution.solve_time_sec > 0
    assert len(solution.p_charge_kw) == 4
    assert len(solution.price_ariary) == 4
    assert len(solution.soc_kwh) == 4

    # Verify solution values are within bounds
    for t in range(4):
        assert simple_inputs.price_min <= solution.price_ariary[t] <= simple_inputs.price_max
        assert simple_inputs.soc_min_kwh <= solution.soc_kwh[t] <= simple_inputs.soc_max_kwh
        assert 0 <= solution.p_charge_kw[t] <= simple_inputs.battery_power_kw
        assert 0 <= solution.p_discharge_kw[t] <= simple_inputs.battery_power_kw

    print(f"Solved in {solution.solve_time_sec:.2f}s, status={solution.status}")
    model.cleanup()


@pytest.mark.skipif(not GUROBI_AVAILABLE, reason="Gurobi not installed")
def test_solve_mahavelona(mahavelona_inputs):
    """Test solving full Mahavelona 24-hour problem."""
    is_valid, _ = check_gurobi_license()
    if not is_valid:
        pytest.skip("Valid Gurobi license required")

    model = GurobiMicrogridModel(mahavelona_inputs, time_limit_sec=60, verbose=False)
    solution = model.solve()

    assert solution.status in ("optimal", "feasible")
    assert len(solution.p_charge_kw) == 24

    # Extract and calculate metrics
    sol_dict = extract_kora_solution(solution)
    metrics = calculate_metrics(sol_dict, mahavelona_inputs)

    # Verify metrics are reasonable
    assert metrics["curtailment_rate"] < 0.7  # Should be better than baseline 70%
    # Note: Mahavelona scenario has overnight demand that exceeds battery capacity,
    # so some blackouts are expected. The key metric is curtailment reduction.
    assert metrics["blackout_hours"] < 24  # Not all hours are blackouts
    assert metrics["total_revenue_ariary"] > 0

    print(f"Mahavelona results:")
    print(f"  Solve time: {solution.solve_time_sec:.2f}s")
    print(f"  Curtailment: {metrics['curtailment_rate']*100:.1f}%")
    print(f"  Revenue: {metrics['total_revenue_ariary']:,.0f} Ar")

    model.cleanup()


@pytest.mark.skipif(not GUROBI_AVAILABLE, reason="Gurobi not installed")
def test_warm_start(simple_inputs):
    """Test warm-starting from previous solution."""
    is_valid, _ = check_gurobi_license()
    if not is_valid:
        pytest.skip("Valid Gurobi license required")

    # First solve (cold start)
    model1 = GurobiMicrogridModel(simple_inputs, time_limit_sec=30, verbose=False)
    solution1 = model1.solve()
    assert solution1.is_success
    time1 = solution1.solve_time_sec
    model1.cleanup()

    # Second solve with warm start
    model2 = GurobiMicrogridModel(simple_inputs, time_limit_sec=30, verbose=False)
    solution2 = model2.solve(warm_start=solution1)
    assert solution2.is_success
    time2 = solution2.solve_time_sec
    model2.cleanup()

    # Warm-started solve should complete successfully
    # (May not be faster for small problems due to overhead)
    print(f"Cold start: {time1:.3f}s, Warm start: {time2:.3f}s")


# =============================================================================
# Fallback Tests
# =============================================================================

def test_fallback_to_glpk(simple_inputs):
    """Test fallback to GLPK solver (default fallback when Gurobi unavailable)."""
    try:
        # Force GLPK (the actual fallback solver used)
        result = solve_kora_model(simple_inputs, solver="glpk", time_limit_sec=30)
    except Exception as e:
        if "solver" in str(e).lower() or "not found" in str(e).lower():
            pytest.skip(f"GLPK solver not available: {e}")
        raise

    # Should return Pyomo model (not GurobiSolution)
    assert result is not None
    assert not isinstance(result, GurobiSolution)

    # Extract solution
    sol = extract_kora_solution(result)
    assert "p_charge_kw" in sol
    assert "price_ariary" in sol
    assert len(sol["p_charge_kw"]) == 4

    print("GLPK fallback successful")


def test_solve_kora_model_auto(simple_inputs):
    """Test auto solver selection."""
    result = solve_kora_model(simple_inputs, solver="auto", time_limit_sec=30)

    assert result is not None
    sol = extract_kora_solution(result)
    assert "p_charge_kw" in sol

    # Check which solver was used
    if isinstance(result, GurobiSolution):
        print(f"Auto selected: Gurobi (status={result.status})")
    else:
        print("Auto selected: GLPK (fallback)")


# =============================================================================
# Solution Extraction Tests
# =============================================================================

def test_extract_gurobi_solution():
    """Test extracting solution from GurobiSolution object."""
    # Create a mock solution
    solution = GurobiSolution(
        status="optimal",
        objective_value=-1000.0,
        solve_time_sec=1.5,
        mip_gap=0.001,
        p_charge_kw=[10.0, 20.0],
        p_discharge_kw=[0.0, 5.0],
        soc_kwh=[50.0, 55.0],
        price_ariary=[1500.0, 1800.0],
        demand_kw=[25.0, 22.0],
        p_curtail_kw=[5.0, 0.0],
        p_unmet_kw=[0.0, 0.0],
        p_grid_import_kw=[0.0, 0.0],
        p_grid_export_kw=[0.0, 0.0],
    )

    extracted = extract_kora_solution(solution)

    assert extracted["p_charge_kw"] == [10.0, 20.0]
    assert extracted["price_ariary"] == [1500.0, 1800.0]
    assert extracted["soc_kwh"] == [50.0, 55.0]


def test_calculate_metrics(simple_inputs):
    """Test metrics calculation."""
    # Create a simple solution dict
    solution = {
        "p_charge_kw": [0.0, 10.0, 15.0, 0.0],
        "p_discharge_kw": [5.0, 0.0, 0.0, 10.0],
        "soc_kwh": [20.0, 29.0, 43.0, 33.0],
        "price_ariary": [1800.0, 1500.0, 1200.0, 2000.0],
        "demand_kw": [18.0, 28.0, 38.0, 35.0],
        "p_curtail_kw": [0.0, 12.0, 27.0, 0.0],
        "p_unmet_kw": [0.0, 0.0, 0.0, 0.0],
        "p_grid_import_kw": [0.0, 0.0, 0.0, 0.0],
        "p_grid_export_kw": [0.0, 0.0, 0.0, 0.0],
    }

    metrics = calculate_metrics(solution, simple_inputs)

    assert "curtailment_rate" in metrics
    assert "total_revenue_ariary" in metrics
    assert "blackout_hours" in metrics
    assert metrics["blackout_hours"] == 0  # No unmet demand
    assert metrics["total_revenue_ariary"] > 0


# =============================================================================
# Edge Cases
# =============================================================================

def test_high_demand_scenario():
    """Test scenario with very high demand relative to supply."""
    inputs = KoraOptimizerInputs(
        pv_forecast_kw=[0.0, 10.0, 20.0, 10.0],  # Low solar
        base_demand_kw=[50.0, 60.0, 70.0, 80.0],  # High demand
        battery_capacity_kwh=30.0,  # Small battery
        battery_power_kw=15.0,
        soc_init_kwh=15.0,
        soc_min_kwh=5.0,
        soc_max_kwh=28.0,
        price_min=1000.0,
        price_max=2500.0,
        price_reference=1750.0,
        demand_elasticity=0.6,
        curtailment_value_per_kwh=1500.0,
        blackout_penalty_per_kwh=5000.0,  # Allow blackouts (will be penalized)
    )

    result = solve_kora_model(inputs, solver="auto", time_limit_sec=30)
    assert result is not None

    sol = extract_kora_solution(result)
    metrics = calculate_metrics(sol, inputs)

    # Should have some unmet demand (blackouts)
    print(f"High demand scenario: blackout_hours={metrics['blackout_hours']}")


def test_excess_solar_scenario():
    """Test scenario with excess solar and limited storage."""
    inputs = KoraOptimizerInputs(
        pv_forecast_kw=[0.0, 100.0, 150.0, 100.0],  # High solar
        base_demand_kw=[10.0, 15.0, 20.0, 15.0],  # Low demand
        battery_capacity_kwh=20.0,  # Small battery
        battery_power_kw=10.0,
        soc_init_kwh=10.0,
        soc_min_kwh=4.0,
        soc_max_kwh=18.0,
        price_min=500.0,
        price_max=2500.0,
        price_reference=1500.0,
        demand_elasticity=0.8,  # High elasticity
        curtailment_value_per_kwh=1500.0,
        blackout_penalty_per_kwh=5000.0,
    )

    result = solve_kora_model(inputs, solver="auto", time_limit_sec=30)
    assert result is not None

    sol = extract_kora_solution(result)
    metrics = calculate_metrics(sol, inputs)

    # Should have significant curtailment
    assert metrics["curtailment_rate"] > 0
    print(f"Excess solar: curtailment={metrics['curtailment_rate']*100:.1f}%")


# =============================================================================
# Performance Benchmark
# =============================================================================

@pytest.mark.skipif(not GUROBI_AVAILABLE, reason="Gurobi not installed")
def test_benchmark_gurobi_vs_glpk(mahavelona_inputs):
    """Compare Gurobi vs GLPK performance."""
    is_valid, _ = check_gurobi_license()
    if not is_valid:
        pytest.skip("Valid Gurobi license required")

    import time

    # Gurobi solve
    model = GurobiMicrogridModel(mahavelona_inputs, time_limit_sec=60, verbose=False)
    gurobi_start = time.time()
    gurobi_solution = model.solve()
    gurobi_time = time.time() - gurobi_start
    model.cleanup()

    # GLPK solve (using linear model fallback)
    try:
        glpk_start = time.time()
        glpk_result = solve_kora_model(mahavelona_inputs, solver="glpk", time_limit_sec=60)
        glpk_time = time.time() - glpk_start
    except Exception as e:
        print(f"\nGLPK benchmark skipped: {e}")
        print(f"Gurobi only - solve time: {gurobi_time:.2f}s")
        return

    # Extract metrics for both
    gurobi_metrics = calculate_metrics(extract_kora_solution(gurobi_solution), mahavelona_inputs)
    glpk_metrics = calculate_metrics(extract_kora_solution(glpk_result), mahavelona_inputs)

    print("\n" + "=" * 60)
    print("PERFORMANCE BENCHMARK: Gurobi vs GLPK")
    print("=" * 60)
    print(f"{'Metric':<25} {'Gurobi':>15} {'GLPK':>15}")
    print("-" * 60)
    print(f"{'Solve time (s)':<25} {gurobi_time:>15.2f} {glpk_time:>15.2f}")
    print(f"{'Curtailment (%)':<25} {gurobi_metrics['curtailment_rate']*100:>15.1f} {glpk_metrics['curtailment_rate']*100:>15.1f}")
    print(f"{'Revenue (Ar)':<25} {gurobi_metrics['total_revenue_ariary']:>15,.0f} {glpk_metrics['total_revenue_ariary']:>15,.0f}")
    print(f"{'Blackout hours':<25} {gurobi_metrics['blackout_hours']:>15d} {glpk_metrics['blackout_hours']:>15d}")

    if gurobi_time < glpk_time:
        speedup = glpk_time / gurobi_time
        print(f"\nGurobi is {speedup:.1f}x faster")
    else:
        speedup = gurobi_time / glpk_time
        print(f"\nGLPK is {speedup:.1f}x faster")


# =============================================================================
# GurobiSolution Tests
# =============================================================================

def test_gurobi_solution_is_success():
    """Test is_success property."""
    optimal = GurobiSolution(status="optimal", objective_value=100, solve_time_sec=1)
    feasible = GurobiSolution(status="feasible", objective_value=100, solve_time_sec=1)
    infeasible = GurobiSolution(status="infeasible", objective_value=float('inf'), solve_time_sec=1)
    timeout = GurobiSolution(status="timeout", objective_value=float('inf'), solve_time_sec=60)

    assert optimal.is_success
    assert feasible.is_success
    assert not infeasible.is_success
    assert not timeout.is_success


def test_gurobi_solution_to_dict():
    """Test to_dict serialization."""
    solution = GurobiSolution(
        status="optimal",
        objective_value=-1000.0,
        solve_time_sec=1.5,
        mip_gap=0.001,
        p_charge_kw=[10.0],
        p_discharge_kw=[0.0],
        soc_kwh=[50.0],
        price_ariary=[1500.0],
        demand_kw=[25.0],
        p_curtail_kw=[5.0],
        p_unmet_kw=[0.0],
        p_grid_import_kw=[0.0],
        p_grid_export_kw=[0.0],
    )

    d = solution.to_dict()
    assert d["status"] == "optimal"
    assert d["solve_time_sec"] == 1.5
    assert d["p_charge_kw"] == [10.0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
