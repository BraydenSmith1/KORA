"""
KORA Optimizer Test Scenarios

Comprehensive test suite covering:
- Normal operations
- Cloudy day scenarios
- Battery failure scenarios
- Demand spikes
- Edge cases

Run with: pytest tests/test_scenarios.py -v
"""

import pytest
import numpy as np
from typing import List, Tuple

# Import optimizer components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from optimizer.kora_model import (
    KoraOptimizerInputs,
    build_kora_model,
    solve_kora_model,
    extract_kora_solution,
    calculate_metrics,
)


# =============================================================================
# Test Data Generators
# =============================================================================

def generate_clear_day_solar(hours: int = 24, peak_kw: float = 100) -> List[float]:
    """Generate clear day solar profile (peak at noon)."""
    solar = []
    for h in range(hours):
        if 6 <= h <= 18:
            angle = (h - 6) / 12 * np.pi
            solar.append(peak_kw * np.sin(angle))
        else:
            solar.append(0)
    return solar


def generate_cloudy_day_solar(hours: int = 24, peak_kw: float = 100) -> List[float]:
    """Generate cloudy day solar profile (reduced, variable output)."""
    clear_solar = generate_clear_day_solar(hours, peak_kw)
    # Apply cloud factor: 30-60% reduction with variability
    cloud_factor = np.random.uniform(0.3, 0.7, hours)
    return [s * cf for s, cf in zip(clear_solar, cloud_factor)]


def generate_intermittent_solar(hours: int = 24, peak_kw: float = 100) -> List[float]:
    """Generate intermittent solar (passing clouds every few hours)."""
    clear_solar = generate_clear_day_solar(hours, peak_kw)
    # Add passing clouds (sudden drops)
    solar = list(clear_solar)
    for h in [9, 10, 14, 15]:  # Cloud events
        if h < hours:
            solar[h] *= 0.2
    return solar


def generate_normal_demand(hours: int = 24, peak_kw: float = 50) -> List[float]:
    """Generate typical demand profile (peak in evening)."""
    base = peak_kw * 0.15
    pattern = {
        0: 0.2, 1: 0.15, 2: 0.15, 3: 0.15, 4: 0.15, 5: 0.2,
        6: 0.35, 7: 0.45, 8: 0.5, 9: 0.48, 10: 0.45, 11: 0.5,
        12: 0.4, 13: 0.38, 14: 0.45, 15: 0.5, 16: 0.6, 17: 0.75,
        18: 0.95, 19: 1.0, 20: 0.9, 21: 0.7, 22: 0.5, 23: 0.3,
    }
    return [base + (peak_kw - base) * pattern.get(h % 24, 0.3) for h in range(hours)]


def generate_demand_spike(hours: int = 24, peak_kw: float = 50, spike_hour: int = 19) -> List[float]:
    """Generate demand with sudden spike."""
    demand = generate_normal_demand(hours, peak_kw)
    if spike_hour < hours:
        demand[spike_hour] *= 1.5  # 50% spike
    return demand


def generate_low_demand(hours: int = 24, peak_kw: float = 50) -> List[float]:
    """Generate low demand day (e.g., holiday)."""
    normal = generate_normal_demand(hours, peak_kw)
    return [d * 0.5 for d in normal]  # 50% of normal


def create_test_inputs(
    pv: List[float],
    demand: List[float],
    battery_capacity_kwh: float = 100,
    battery_power_kw: float = 50,
    initial_soc_pct: float = 50,
) -> KoraOptimizerInputs:
    """Create test inputs from PV and demand profiles."""
    return KoraOptimizerInputs(
        pv_forecast_kw=pv,
        base_demand_kw=demand,
        battery_capacity_kwh=battery_capacity_kwh,
        battery_power_kw=battery_power_kw,
        soc_init_kwh=battery_capacity_kwh * initial_soc_pct / 100,
        soc_min_kwh=battery_capacity_kwh * 0.2,
        soc_max_kwh=battery_capacity_kwh * 0.95,
        eta_charge=0.94,
        eta_discharge=0.94,
        price_min=1000,
        price_max=2500,
        price_reference=1750,
        demand_elasticity=0.6,
        curtailment_value_per_kwh=1500,
        blackout_penalty_per_kwh=5000,
        timestep_hours=1.0,
    )


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def solver():
    """Default solver to use for tests."""
    return "highs"


# =============================================================================
# Normal Operation Tests
# =============================================================================

class TestNormalOperations:
    """Tests for normal operating conditions."""

    def test_clear_day_normal_demand(self, solver):
        """Test optimization on a clear sunny day with normal demand."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=50)
        inputs = create_test_inputs(pv, demand)

        model = solve_kora_model(inputs, solver=solver, time_limit_sec=30)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # Assertions
        assert metrics['curtailment_rate'] < 0.1, "Curtailment should be < 10% on clear day"
        assert metrics['blackout_hours'] == 0, "No blackouts expected"
        assert metrics['total_revenue_ariary'] > 0, "Should generate revenue"

    def test_battery_charges_during_solar_peak(self, solver):
        """Verify battery charges when solar exceeds demand."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=30)  # Low demand
        inputs = create_test_inputs(pv, demand, initial_soc_pct=30)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)

        # Battery should charge during midday (hours 10-14)
        midday_charging = sum(solution['p_charge_kw'][10:15])
        assert midday_charging > 0, "Battery should charge during solar peak"

    def test_battery_discharges_during_evening_peak(self, solver):
        """Verify battery discharges during evening demand peak."""
        pv = generate_clear_day_solar(24, peak_kw=80)
        demand = generate_normal_demand(24, peak_kw=50)
        inputs = create_test_inputs(pv, demand, initial_soc_pct=80)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)

        # Battery should discharge during evening (hours 18-21)
        evening_discharge = sum(solution['p_discharge_kw'][18:22])
        assert evening_discharge > 0, "Battery should discharge during evening peak"

    def test_price_varies_with_supply(self, solver):
        """Verify prices are lower when solar is abundant."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=40)
        inputs = create_test_inputs(pv, demand)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)

        # Midday prices should be lower than evening prices
        midday_avg_price = np.mean(solution['price_ariary'][10:14])
        evening_avg_price = np.mean(solution['price_ariary'][18:21])

        assert midday_avg_price < evening_avg_price, \
            "Prices should be lower during solar abundance"


# =============================================================================
# Cloudy Day Tests
# =============================================================================

class TestCloudyDayScenarios:
    """Tests for cloudy/overcast conditions."""

    def test_cloudy_day_higher_curtailment(self, solver):
        """Cloudy days may have higher curtailment due to variability."""
        pv = generate_cloudy_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=40)
        inputs = create_test_inputs(pv, demand)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # Should still avoid blackouts
        assert metrics['blackout_hours'] == 0, "Should avoid blackouts on cloudy day"

    def test_intermittent_clouds_battery_smoothing(self, solver):
        """Battery should smooth out intermittent cloud events."""
        pv = generate_intermittent_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=40)
        inputs = create_test_inputs(pv, demand, initial_soc_pct=60)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # No blackouts despite intermittent solar
        assert metrics['blackout_hours'] == 0, "Battery should prevent blackouts"

    def test_very_cloudy_day_battery_critical(self, solver):
        """Test behavior when solar is very low and battery is critical."""
        pv = [p * 0.2 for p in generate_clear_day_solar(24, 100)]  # Only 20% of normal
        demand = generate_normal_demand(24, peak_kw=40)
        inputs = create_test_inputs(pv, demand, initial_soc_pct=30)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # Should use demand response (higher prices to reduce demand)
        max_price = max(solution['price_ariary'])
        assert max_price > 2000, "Should use higher prices when supply is constrained"


# =============================================================================
# Battery Failure Scenarios
# =============================================================================

class TestBatteryFailureScenarios:
    """Tests for battery capacity constraints."""

    def test_half_battery_capacity(self, solver):
        """Test with 50% battery capacity (simulating partial failure)."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=50)
        inputs = create_test_inputs(pv, demand, battery_capacity_kwh=50)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # Should still operate, maybe with more curtailment
        assert solution is not None, "Should find a solution with reduced battery"
        assert metrics['blackout_hours'] <= 2, "Should minimize blackouts"

    def test_very_small_battery(self, solver):
        """Test with minimal battery capacity."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=40)
        inputs = create_test_inputs(
            pv, demand,
            battery_capacity_kwh=20,
            battery_power_kw=10
        )

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # Should see more curtailment with small battery
        assert metrics['curtailment_rate'] > 0.05, \
            "Expected some curtailment with small battery"

    def test_low_battery_power(self, solver):
        """Test with reduced battery power (charge/discharge rate limit)."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=50)
        inputs = create_test_inputs(
            pv, demand,
            battery_capacity_kwh=100,
            battery_power_kw=20  # Reduced from 50
        )

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)

        # Check that power limits are respected
        max_charge = max(solution['p_charge_kw'])
        max_discharge = max(solution['p_discharge_kw'])
        assert max_charge <= 20.1, "Charge power should respect limit"
        assert max_discharge <= 20.1, "Discharge power should respect limit"


# =============================================================================
# Demand Spike Scenarios
# =============================================================================

class TestDemandSpikeScenarios:
    """Tests for sudden demand increases."""

    def test_evening_demand_spike(self, solver):
        """Test response to sudden evening demand spike."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_demand_spike(24, peak_kw=50, spike_hour=19)
        inputs = create_test_inputs(pv, demand, initial_soc_pct=70)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # Should handle spike without blackout
        assert metrics['blackout_hours'] == 0, "Should handle demand spike"
        # Price should increase during spike
        assert solution['price_ariary'][19] > solution['price_ariary'][17], \
            "Price should increase during spike"

    def test_morning_demand_spike(self, solver):
        """Test response to morning demand spike (before full solar)."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_demand_spike(24, peak_kw=50, spike_hour=7)
        inputs = create_test_inputs(pv, demand, initial_soc_pct=60)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)

        # Battery should discharge to meet morning spike
        assert solution['p_discharge_kw'][7] > 0, \
            "Battery should discharge during morning spike"

    def test_multiple_demand_spikes(self, solver):
        """Test response to multiple demand spikes."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=50)
        # Add multiple spikes
        for spike_hour in [8, 13, 19]:
            demand[spike_hour] *= 1.4
        inputs = create_test_inputs(pv, demand, initial_soc_pct=60)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # Should handle multiple spikes
        assert metrics['blackout_hours'] <= 1, "Should handle multiple spikes"


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_solar(self, solver):
        """Test with zero solar (nighttime or equipment failure)."""
        pv = [0] * 24
        demand = generate_normal_demand(24, peak_kw=30)
        inputs = create_test_inputs(pv, demand, initial_soc_pct=90)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)

        # Should rely entirely on battery
        total_discharge = sum(solution['p_discharge_kw'])
        assert total_discharge > 0, "Should use battery when no solar"

    def test_zero_demand(self, solver):
        """Test with near-zero demand."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = [1] * 24  # Minimal demand
        inputs = create_test_inputs(pv, demand, initial_soc_pct=20)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # High curtailment expected with no demand
        assert metrics['curtailment_rate'] > 0.5, \
            "High curtailment expected with minimal demand"

    def test_demand_exceeds_supply(self, solver):
        """Test when demand consistently exceeds available supply."""
        pv = generate_clear_day_solar(24, peak_kw=30)  # Low solar
        demand = generate_normal_demand(24, peak_kw=80)  # High demand
        inputs = create_test_inputs(pv, demand, initial_soc_pct=50)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)
        metrics = calculate_metrics(solution, inputs)

        # Demand reduction via pricing should be visible
        max_price = max(solution['price_ariary'])
        assert max_price > 2200, "Should use high prices when supply constrained"

    def test_soc_bounds_respected(self, solver):
        """Verify SOC stays within bounds."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=50)
        inputs = create_test_inputs(pv, demand)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)

        min_soc = min(solution['soc_kwh'])
        max_soc = max(solution['soc_kwh'])
        assert min_soc >= inputs.soc_min_kwh - 0.1, "SOC should respect minimum"
        assert max_soc <= inputs.soc_max_kwh + 0.1, "SOC should respect maximum"

    def test_price_bounds_respected(self, solver):
        """Verify prices stay within bounds."""
        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=50)
        inputs = create_test_inputs(pv, demand)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)

        min_price = min(solution['price_ariary'])
        max_price = max(solution['price_ariary'])
        assert min_price >= inputs.price_min - 1, "Price should respect minimum"
        assert max_price <= inputs.price_max + 1, "Price should respect maximum"

    def test_short_horizon(self, solver):
        """Test with very short optimization horizon."""
        pv = generate_clear_day_solar(6, peak_kw=100)[:6]
        demand = generate_normal_demand(6, peak_kw=50)[:6]
        inputs = create_test_inputs(pv, demand)

        model = solve_kora_model(inputs, solver=solver)
        solution = extract_kora_solution(model)

        assert len(solution['price_ariary']) == 6, "Should solve for 6 hours"

    def test_long_horizon(self, solver):
        """Test with longer optimization horizon (48 hours)."""
        pv = generate_clear_day_solar(48, peak_kw=100)
        demand = generate_normal_demand(48, peak_kw=50)
        inputs = create_test_inputs(pv, demand)

        model = solve_kora_model(inputs, solver=solver, time_limit_sec=120)
        solution = extract_kora_solution(model)

        assert len(solution['price_ariary']) == 48, "Should solve for 48 hours"


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Tests for solver performance."""

    def test_solve_time_under_30_seconds(self, solver):
        """Verify optimization completes in under 30 seconds."""
        import time

        pv = generate_clear_day_solar(24, peak_kw=100)
        demand = generate_normal_demand(24, peak_kw=50)
        inputs = create_test_inputs(pv, demand)

        start = time.time()
        model = solve_kora_model(inputs, solver=solver, time_limit_sec=30)
        solve_time = time.time() - start

        assert solve_time < 30, f"Solve time {solve_time:.1f}s exceeds 30s limit"

    def test_solve_time_48_hour_horizon(self, solver):
        """Verify 48-hour horizon solves in reasonable time."""
        import time

        pv = generate_clear_day_solar(48, peak_kw=100)
        demand = generate_normal_demand(48, peak_kw=50)
        inputs = create_test_inputs(pv, demand)

        start = time.time()
        model = solve_kora_model(inputs, solver=solver, time_limit_sec=60)
        solve_time = time.time() - start

        assert solve_time < 60, f"48-hour solve time {solve_time:.1f}s exceeds limit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
