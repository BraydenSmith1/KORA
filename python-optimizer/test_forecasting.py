#!/usr/bin/env python3
"""
Test script for KORA Forecasting Service.

Run from python-optimizer directory:
    python test_forecasting.py
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_weather_api():
    """Test Open-Meteo weather API integration."""
    print("\n" + "="*60)
    print("TEST 1: Weather API (Open-Meteo)")
    print("="*60)

    from kora.forecasting import OpenMeteoClient

    # Mahavelona coordinates
    client = OpenMeteoClient(latitude=-18.9, longitude=47.5)

    try:
        weather = client.get_forecast(hours=24)
        print(f"  Fetched {len(weather)} hours of weather data")
        print(f"  First hour: {weather[0].time}")
        print(f"    GHI: {weather[0].ghi:.1f} W/m²")
        print(f"    Temperature: {weather[0].temperature:.1f}°C")
        print(f"    Cloud cover: {weather[0].cloud_cover:.0f}%")

        # Find peak solar hour
        peak_hour = max(weather, key=lambda w: w.ghi)
        print(f"  Peak solar at {peak_hour.time.hour}:00 - GHI: {peak_hour.ghi:.1f} W/m²")

        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def test_pv_forecaster():
    """Test PV forecaster with real weather data."""
    print("\n" + "="*60)
    print("TEST 2: PV Forecaster (Physics-based)")
    print("="*60)

    from kora.forecasting import PVForecaster

    forecaster = PVForecaster(
        capacity_kwp=118.5,  # Mahavelona
        latitude=-18.9,
        longitude=47.5,
        site_id="mahavelona"
    )

    # Validate inputs
    errors = forecaster.validate_inputs()
    if errors:
        print(f"  Validation errors: {errors}")
        return False

    try:
        result = forecaster.forecast(hours=24)
        print(f"  Generated {result.horizon_hours}-hour PV forecast")
        print(f"  Method: {result.method}")
        print(f"  Total expected energy: {sum(result.values):.1f} kWh")

        # Find peak hour
        peak_idx = result.values.index(max(result.values))
        print(f"  Peak output: {max(result.values):.1f} kW at hour {peak_idx}")

        # Show first 12 hours
        print("  Hourly forecast (first 12h):")
        for i, val in enumerate(result.values[:12]):
            bar = "█" * int(val / 5)
            print(f"    {i:2d}:00 - {val:6.1f} kW {bar}")

        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_demand_forecaster():
    """Test demand forecaster with pattern model."""
    print("\n" + "="*60)
    print("TEST 3: Demand Forecaster (Pattern-based)")
    print("="*60)

    from kora.forecasting import DemandForecaster

    forecaster = DemandForecaster(
        peak_load_kw=53.0,
        base_load_kw=8.0,
        elasticity=0.6,
        customer_count=251,
        site_id="mahavelona"
    )

    try:
        result = forecaster.forecast(hours=24, add_noise=False)
        print(f"  Generated {result.horizon_hours}-hour demand forecast")
        print(f"  Method: {result.method}")
        print(f"  Total expected consumption: {sum(result.values):.1f} kWh")

        # Find peak hour
        peak_idx = result.values.index(max(result.values))
        print(f"  Peak demand: {max(result.values):.1f} kW at hour {peak_idx}")

        # Test with price schedule
        price_schedule = [1750] * 12 + [2200] * 6 + [1500] * 6  # High price evening
        result_priced = forecaster.forecast(hours=24, price_schedule=price_schedule, add_noise=False)
        print(f"  With dynamic pricing: {sum(result_priced.values):.1f} kWh")
        print(f"  Demand reduction: {(1 - sum(result_priced.values)/sum(result.values))*100:.1f}%")

        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def test_soc_projector():
    """Test battery SoC projector."""
    print("\n" + "="*60)
    print("TEST 4: SoC Projector (Physics-based)")
    print("="*60)

    from kora.forecasting import SoCProjector, PVForecaster, DemandForecaster

    # Get forecasts
    pv_forecaster = PVForecaster(capacity_kwp=118.5)
    demand_forecaster = DemandForecaster(peak_load_kw=53.0)

    pv = pv_forecaster.forecast(24)
    demand = demand_forecaster.forecast(24, add_noise=False)

    projector = SoCProjector(
        capacity_kwh=115.0,
        power_kw=54.0,
        soc_min_pct=20.0,
        soc_max_pct=95.0
    )

    try:
        # Start at 50% SoC
        initial_soc = 57.5  # 50% of 115 kWh

        projection = projector.project(
            initial_soc_kwh=initial_soc,
            pv_forecast=pv.values,
            demand_forecast=demand.values
        )

        print(f"  Initial SoC: {initial_soc:.1f} kWh ({initial_soc/115*100:.0f}%)")
        print(f"  Final SoC: {projection.soc_kwh[-1]:.1f} kWh ({projection.soc_percent[-1]:.0f}%)")
        print(f"  Warnings: {len(projection.warnings)}")

        if projection.warnings:
            for w in projection.warnings[:3]:
                print(f"    - {w}")

        print(f"  Min SoC reached: {projection.min_soc_reached}")
        print(f"  Max SoC reached: {projection.max_soc_reached}")

        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_risk_calculator():
    """Test outage risk calculator."""
    print("\n" + "="*60)
    print("TEST 5: Outage Risk Calculator")
    print("="*60)

    from kora.forecasting import (
        OutageRiskCalculator, SoCProjector,
        PVForecaster, DemandForecaster
    )

    # Get forecasts and projection
    pv = PVForecaster(capacity_kwp=118.5).forecast(24)
    demand = DemandForecaster(peak_load_kw=53.0).forecast(24, add_noise=False)

    projector = SoCProjector(capacity_kwh=115.0, power_kw=54.0)
    soc_projection = projector.project(
        initial_soc_kwh=57.5,  # 50%
        pv_forecast=pv.values,
        demand_forecast=demand.values
    )

    calculator = OutageRiskCalculator(
        battery_capacity_kwh=115.0,
        battery_power_kw=54.0,
        peak_demand_kw=53.0
    )

    try:
        risk = calculator.assess(
            soc_projection=soc_projection,
            pv_forecast=pv.values,
            demand_forecast=demand.values
        )

        print(f"  Alert Level: {risk.alert_level.upper()}")
        print(f"  Overall Risk: {risk.overall_risk:.2f}")
        print(f"    - SoC Risk: {risk.soc_risk:.2f}")
        print(f"    - Demand Risk: {risk.demand_risk:.2f}")
        print(f"    - Weather Risk: {risk.weather_risk:.2f}")
        print(f"  Low SoC Hours: {risk.low_soc_hours}")
        print(f"  Peak Deficit: {risk.peak_deficit_kw:.1f} kW")

        if risk.recommendations:
            print("  Recommendations:")
            for rec in risk.recommendations[:3]:
                print(f"    - {rec}")

        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_forecast_service():
    """Test the main ForecastService interface."""
    print("\n" + "="*60)
    print("TEST 6: ForecastService (Main Interface)")
    print("="*60)

    from kora.forecasting import ForecastService

    try:
        # Create service with Mahavelona defaults
        service = ForecastService.create_default(
            latitude=-18.9,
            longitude=47.5,
            site_id="mahavelona"
        )

        # Validate configuration
        errors = service.validate()
        if errors:
            print(f"  Validation errors: {errors}")
            return False

        # Get daily summary
        summary = service.get_daily_summary(initial_soc_kwh=57.5)

        print(f"  Site: {summary['site_id']}")
        print(f"  PV Forecast: {summary['pv_forecast_kwh']:.1f} kWh")
        print(f"  Demand Forecast: {summary['demand_forecast_kwh']:.1f} kWh")
        print(f"  Surplus: {summary['surplus_kwh']:.1f} kWh")
        print(f"  Peak PV: {summary['peak_pv_kw']:.1f} kW")
        print(f"  Peak Demand: {summary['peak_demand_kw']:.1f} kW")
        print(f"  Risk Level: {summary['risk_level']}")

        # Get forecast providers for optimizer integration
        pv_provider, demand_provider = service.get_forecast_providers()
        pv_values = pv_provider()
        demand_values = demand_provider()

        print(f"\n  Optimizer Integration Test:")
        print(f"    PV provider returns: {len(pv_values)} hourly values")
        print(f"    Demand provider returns: {len(demand_values)} hourly values")

        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("KORA FORECASTING SERVICE - TEST SUITE")
    print("="*60)

    tests = [
        ("Weather API", test_weather_api),
        ("PV Forecaster", test_pv_forecaster),
        ("Demand Forecaster", test_demand_forecaster),
        ("SoC Projector", test_soc_projector),
        ("Risk Calculator", test_risk_calculator),
        ("Forecast Service", test_forecast_service),
    ]

    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, passed))
        except Exception as e:
            logger.error(f"Test {name} crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, p in results:
        status = "PASS" if p else "FAIL"
        print(f"  {name}: {status}")

    print(f"\n  Total: {passed}/{total} passed")

    if passed == total:
        print("\n  All tests passed!")
        return 0
    else:
        print("\n  Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
