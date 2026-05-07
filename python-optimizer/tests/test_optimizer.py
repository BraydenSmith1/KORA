"""
Tests for KORA optimizer with edge cases.
"""

import pytest
import numpy as np
from typing import List

# Import will fail if dependencies aren't installed, skip gracefully
pytest.importorskip("pyomo")


class TestKoraOptimizer:
    """Test the KORA optimization model."""

    @pytest.fixture
    def sample_inputs(self):
        """Create sample inputs for testing."""
        from optimizer.kora_model import KoraOptimizerInputs

        hours = 24
        # Simple sinusoidal profiles
        pv = [max(0, 50 * np.sin((h - 6) / 12 * np.pi)) for h in range(hours)]
        demand = [20 + 10 * np.sin((h - 18) / 12 * np.pi) for h in range(hours)]

        return KoraOptimizerInputs(
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

    def test_model_builds(self, sample_inputs):
        """Test that model builds without errors."""
        from optimizer.kora_model import build_kora_model

        model = build_kora_model(sample_inputs)

        assert model is not None
        assert hasattr(model, "obj")
        assert hasattr(model, "p_charge")
        assert hasattr(model, "price")

    def test_model_solves(self, sample_inputs):
        """Test that model solves successfully."""
        from optimizer.kora_model import solve_kora_model, extract_kora_solution

        model = solve_kora_model(sample_inputs, solver="highs", time_limit_sec=30)
        solution = extract_kora_solution(model)

        assert "price_ariary" in solution
        assert "p_charge_kw" in solution
        assert "p_curtail_kw" in solution
        assert len(solution["price_ariary"]) == 24

    def test_price_bounds_respected(self, sample_inputs):
        """Test that prices stay within configured bounds."""
        from optimizer.kora_model import solve_kora_model, extract_kora_solution

        model = solve_kora_model(sample_inputs, solver="highs")
        solution = extract_kora_solution(model)

        for price in solution["price_ariary"]:
            assert sample_inputs.price_min <= price <= sample_inputs.price_max

    def test_soc_bounds_respected(self, sample_inputs):
        """Test that SOC stays within configured bounds."""
        from optimizer.kora_model import solve_kora_model, extract_kora_solution

        model = solve_kora_model(sample_inputs, solver="highs")
        solution = extract_kora_solution(model)

        for soc in solution["soc_kwh"]:
            assert sample_inputs.soc_min_kwh <= soc <= sample_inputs.soc_max_kwh

    def test_metrics_calculation(self, sample_inputs):
        """Test that metrics are calculated correctly."""
        from optimizer.kora_model import (
            solve_kora_model,
            extract_kora_solution,
            calculate_metrics,
        )

        model = solve_kora_model(sample_inputs, solver="highs")
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, sample_inputs)

        assert "total_pv_kwh" in metrics
        assert "curtailment_rate" in metrics
        assert "total_revenue_ariary" in metrics
        assert 0 <= metrics["curtailment_rate"] <= 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_solar(self):
        """Test with no solar production."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
        )

        inputs = KoraOptimizerInputs(
            pv_forecast_kw=[0] * 24,  # No solar
            base_demand_kw=[20] * 24,
            battery_capacity_kwh=100,
            battery_power_kw=50,
            soc_init_kwh=90,  # Start with full battery
            soc_min_kwh=20,
            soc_max_kwh=95,
            price_min=1000,
            price_max=2500,
            price_reference=1750,
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)

        # Should have no curtailment (nothing to curtail)
        assert sum(solution["p_curtail_kw"]) < 0.01

    def test_zero_demand(self):
        """Test with no demand."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
        )

        inputs = KoraOptimizerInputs(
            pv_forecast_kw=[50] * 24,
            base_demand_kw=[0] * 24,  # No demand
            battery_capacity_kwh=100,
            battery_power_kw=50,
            soc_init_kwh=20,
            soc_min_kwh=20,
            soc_max_kwh=95,
            price_min=1000,
            price_max=2500,
            price_reference=1750,
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)

        # Battery should charge, and excess should be curtailed
        assert sum(solution["p_charge_kw"]) > 0 or sum(solution["p_curtail_kw"]) > 0

    def test_full_battery_start(self):
        """Test starting with full battery."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
        )

        inputs = KoraOptimizerInputs(
            pv_forecast_kw=[100] * 24,  # High solar
            base_demand_kw=[20] * 24,
            battery_capacity_kwh=100,
            battery_power_kw=50,
            soc_init_kwh=95,  # Start full
            soc_min_kwh=20,
            soc_max_kwh=95,
            price_min=1000,
            price_max=2500,
            price_reference=1750,
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)

        # Should discharge to make room, or curtail
        total_discharge = sum(solution["p_discharge_kw"])
        total_curtail = sum(solution["p_curtail_kw"])
        assert total_discharge > 0 or total_curtail > 0

    def test_empty_battery_start(self):
        """Test starting with empty battery."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
        )

        inputs = KoraOptimizerInputs(
            pv_forecast_kw=[50] * 24,
            base_demand_kw=[60] * 24,  # Higher than solar
            battery_capacity_kwh=100,
            battery_power_kw=50,
            soc_init_kwh=20,  # Start at minimum
            soc_min_kwh=20,
            soc_max_kwh=95,
            price_min=1000,
            price_max=2500,
            price_reference=1750,
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)

        # Should have some unmet demand or price adjustment
        assert model is not None

    def test_high_elasticity(self):
        """Test with high demand elasticity."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
            calculate_metrics,
        )

        inputs = KoraOptimizerInputs(
            pv_forecast_kw=[80] * 24,
            base_demand_kw=[30] * 24,
            battery_capacity_kwh=100,
            battery_power_kw=50,
            soc_init_kwh=50,
            soc_min_kwh=20,
            soc_max_kwh=95,
            price_min=1000,
            price_max=2500,
            price_reference=1750,
            demand_elasticity=1.0,  # High elasticity
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # With high elasticity, should reduce curtailment more
        assert metrics["curtailment_rate"] < 0.5  # Should be low

    def test_narrow_price_bounds(self):
        """Test with narrow price bounds."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
        )

        inputs = KoraOptimizerInputs(
            pv_forecast_kw=[50] * 24,
            base_demand_kw=[30] * 24,
            battery_capacity_kwh=100,
            battery_power_kw=50,
            soc_init_kwh=50,
            soc_min_kwh=20,
            soc_max_kwh=95,
            price_min=1700,  # Narrow range
            price_max=1800,
            price_reference=1750,
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)

        # Prices should still be within bounds
        for price in solution["price_ariary"]:
            assert 1700 <= price <= 1800

    def test_short_horizon(self):
        """Test with very short optimization horizon."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
        )

        inputs = KoraOptimizerInputs(
            pv_forecast_kw=[50, 60, 40],  # 3 hours only
            base_demand_kw=[30, 35, 25],
            battery_capacity_kwh=100,
            battery_power_kw=50,
            soc_init_kwh=50,
            soc_min_kwh=20,
            soc_max_kwh=95,
            price_min=1000,
            price_max=2500,
            price_reference=1750,
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)

        assert len(solution["price_ariary"]) == 3


class TestCloudyDayScenarios:
    """Test scenarios with variable/cloudy solar."""

    def test_cloudy_morning(self):
        """Test with clouds in the morning."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
        )

        # Clouds in morning, clear afternoon
        pv = [0, 0, 0, 5, 10, 15, 80, 90, 100, 95, 80, 60, 40, 20, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        demand = [15] * 24

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
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)

        assert model is not None
        assert len(solution["price_ariary"]) == 24

    def test_intermittent_clouds(self):
        """Test with intermittent cloud cover."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
        )

        # Intermittent solar with dips
        pv = [0, 0, 0, 10, 40, 80, 30, 90, 50, 95, 40, 70, 30, 20, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        demand = [20] * 24

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
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)

        assert model is not None


class TestDemandSpikes:
    """Test scenarios with demand spikes."""

    def test_evening_peak(self):
        """Test handling of evening demand peak."""
        from optimizer.kora_model import (
            KoraOptimizerInputs,
            solve_kora_model,
            extract_kora_solution,
        )

        pv = [0, 0, 0, 10, 40, 70, 90, 100, 95, 80, 60, 40, 20, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        # Sharp evening peak
        demand = [10, 10, 10, 12, 15, 18, 20, 22, 20, 18, 20, 25, 30, 35, 40, 60, 80, 90, 70, 50, 35, 25, 15, 10]

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
        )

        model = solve_kora_model(inputs, solver="highs")
        solution = extract_kora_solution(model)

        # Battery should discharge during evening peak
        evening_discharge = sum(solution["p_discharge_kw"][16:20])
        assert evening_discharge > 0
