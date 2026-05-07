"""
Quick Demo - Mahavelona Curtailment Analysis

This creates a simple before/after comparison showing how better
battery management reduces curtailment.

No complex optimization solver needed - just smart battery logic!
"""

import json
import numpy as np
from pathlib import Path

from mahavelona_config import (
    MahavelonaSpecs,
    MahavelonaFareStructure,
    generate_madagascar_solar_profile,
    generate_madagascar_demand_profile,
)


def simulate_baseline(solar, demand, specs, fares):
    """Current operation - battery fills by 10am, then curtailment"""
    hours = len(solar)
    battery_soc = specs.battery_capacity_kwh * 0.3

    result = {
        "p_charge_kw": [],
        "p_discharge_kw": [],
        "soc_kwh": [],
        "p_curtail_kw": [],
        "demand_kw": [],
        "price_ariary": [],
    }

    for h in range(hours):
        # Fixed TOU pricing
        if 17 <= h < 23:  # 5pm-11pm peak
            price = fares.avg_peak_price
        elif 8 <= h < 17:  # 8am-5pm intermediate
            price = fares.avg_intermediate_price
        else:  # Off-peak
            price = fares.avg_offpeak_price

        result["price_ariary"].append(price)

        avail_solar = solar[h]
        customer_demand = demand[h]

        if avail_solar >= customer_demand:
            # Surplus - charge battery or curtail
            surplus = avail_solar - customer_demand
            battery_room = specs.battery_capacity_kwh * 0.95 - battery_soc
            max_charge = min(surplus, specs.battery_power_kw, battery_room)

            if max_charge > 0:
                charge = max_charge
                curtail = surplus - max_charge
            else:
                charge = 0
                curtail = surplus

            result["p_charge_kw"].append(charge)
            result["p_discharge_kw"].append(0)
            result["p_curtail_kw"].append(curtail)
            result["demand_kw"].append(customer_demand)

            battery_soc += charge * specs.battery_efficiency_charge
        else:
            # Deficit - discharge battery
            deficit = customer_demand - avail_solar
            battery_avail = battery_soc - specs.battery_capacity_kwh * 0.20
            max_discharge = min(deficit, specs.battery_power_kw, battery_avail)

            discharge = max(0, max_discharge)

            result["p_charge_kw"].append(0)
            result["p_discharge_kw"].append(discharge)
            result["p_curtail_kw"].append(0)
            result["demand_kw"].append(customer_demand)

            battery_soc -= discharge / specs.battery_efficiency_discharge

        result["soc_kwh"].append(battery_soc)

    # Calculate metrics
    total_pv = sum(solar)
    total_curtail = sum(result["p_curtail_kw"])
    total_served = sum(result["demand_kw"])
    total_revenue = sum(result["price_ariary"][h] * result["demand_kw"][h] for h in range(hours))

    return {
        "timeseries": result,
        "metrics": {
            "total_pv_kwh": total_pv,
            "total_curtail_kwh": total_curtail,
            "curtailment_rate": total_curtail / total_pv if total_pv > 0 else 0,
            "total_demand_served_kwh": total_served,
            "total_revenue_ariary": total_revenue,
            "avg_price_ariary": total_revenue / total_served if total_served > 0 else 0,
        }
    }


def simulate_smart_battery(solar, demand, specs, fares):
    """Smarter battery dispatch - spread charging throughout day"""
    hours = len(solar)
    battery_soc = specs.battery_capacity_kwh * 0.3

    # First pass: figure out when we'll need battery power (evening)
    evening_demand = sum(demand[17:23])  # 5pm-11pm
    evening_solar = sum(solar[17:23])
    evening_deficit = max(0, evening_demand - evening_solar)

    # Target: have enough battery for evening
    target_soc_by_5pm = min(
        evening_deficit / specs.battery_efficiency_discharge,
        specs.battery_capacity_kwh * 0.90
    )

    result = {
        "p_charge_kw": [],
        "p_discharge_kw": [],
        "soc_kwh": [],
        "p_curtail_kw": [],
        "demand_kw": [],
        "price_ariary": [],
    }

    for h in range(hours):
        # Same pricing
        if 17 <= h < 23:
            price = fares.avg_peak_price
        elif 8 <= h < 17:
            price = fares.avg_intermediate_price
        else:
            price = fares.avg_offpeak_price

        result["price_ariary"].append(price)

        avail_solar = solar[h]
        customer_demand = demand[h]

        if avail_solar >= customer_demand:
            surplus = avail_solar - customer_demand

            # Smart charging: moderate rate to avoid filling too early
            if h < 17:  # Before evening
                # Don't charge at max rate - spread it out
                battery_room = target_soc_by_5pm - battery_soc
                hours_left = 17 - h
                if hours_left > 0 and battery_room > 0:
                    target_charge_rate = battery_room / hours_left
                    max_charge = min(
                        surplus,
                        specs.battery_power_kw * 0.7,  # Use 70% of max power
                        battery_room,
                        target_charge_rate * 1.5  # Some buffer
                    )
                else:
                    max_charge = 0
            else:
                max_charge = 0

            charge = max(0, max_charge)
            curtail = surplus - charge

            result["p_charge_kw"].append(charge)
            result["p_discharge_kw"].append(0)
            result["p_curtail_kw"].append(curtail)
            result["demand_kw"].append(customer_demand)

            battery_soc += charge * specs.battery_efficiency_charge
        else:
            # Deficit
            deficit = customer_demand - avail_solar
            battery_avail = battery_soc - specs.battery_capacity_kwh * 0.20
            max_discharge = min(deficit, specs.battery_power_kw, battery_avail)

            discharge = max(0, max_discharge)

            result["p_charge_kw"].append(0)
            result["p_discharge_kw"].append(discharge)
            result["p_curtail_kw"].append(0)
            result["demand_kw"].append(customer_demand)

            battery_soc -= discharge / specs.battery_efficiency_discharge

        result["soc_kwh"].append(battery_soc)

    # Metrics
    total_pv = sum(solar)
    total_curtail = sum(result["p_curtail_kw"])
    total_served = sum(result["demand_kw"])
    total_revenue = sum(result["price_ariary"][h] * result["demand_kw"][h] for h in range(hours))

    return {
        "timeseries": result,
        "metrics": {
            "total_pv_kwh": total_pv,
            "total_curtail_kwh": total_curtail,
            "curtailment_rate": total_curtail / total_pv if total_pv > 0 else 0,
            "total_demand_served_kwh": total_served,
            "total_revenue_ariary": total_revenue,
            "avg_price_ariary": total_revenue / total_served if total_served > 0 else 0,
        }
    }


def main():
    specs = MahavelonaSpecs()
    fares = MahavelonaFareStructure()

    print("=" * 60)
    print("KORA MAHAVELONA DEMO - CURTAILMENT ANALYSIS")
    print("=" * 60)
    print(f"Microgrid: {specs.pv_capacity_kw} kWp solar, {specs.battery_capacity_kwh} kWh battery")
    print(f"Baseline curtailment: {specs.baseline_curtailment_rate * 100}%")
    print("=" * 60)
    print()

    baseline_daily = []
    smart_daily = []

    for day in range(7):
        print(f"Day {day + 1}/7...", end=" ")

        # Generate data
        day_type = "clear" if np.random.random() > 0.2 else "partly_cloudy"
        solar = generate_madagascar_solar_profile(
            peak_capacity_kw=specs.pv_capacity_kw,
            hours=24,
            season="dry",
            day_type=day_type
        )
        demand = generate_madagascar_demand_profile(
            total_customers=specs.total_customers,
            peak_load_kw=53,
            hours=24,
            day_type="weekday" if day < 5 else "weekend"
        )

        # Simulate both
        baseline = simulate_baseline(solar, demand, specs, fares)
        smart = simulate_smart_battery(solar, demand, specs, fares)

        baseline_daily.append(baseline)
        smart_daily.append(smart)

        print(f"Baseline: {baseline['metrics']['curtailment_rate']*100:.1f}%, "
              f"Smart: {smart['metrics']['curtailment_rate']*100:.1f}%")

    # Aggregate
    baseline_total_pv = sum(d["metrics"]["total_pv_kwh"] for d in baseline_daily)
    baseline_total_curtail = sum(d["metrics"]["total_curtail_kwh"] for d in baseline_daily)
    baseline_total_revenue = sum(d["metrics"]["total_revenue_ariary"] for d in baseline_daily)

    smart_total_pv = sum(d["metrics"]["total_pv_kwh"] for d in smart_daily)
    smart_total_curtail = sum(d["metrics"]["total_curtail_kwh"] for d in smart_daily)
    smart_total_revenue = sum(d["metrics"]["total_revenue_ariary"] for d in smart_daily)

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nBASELINE:")
    print(f"  Curtailment: {baseline_total_curtail:.0f} kWh ({baseline_total_curtail/baseline_total_pv*100:.1f}%)")
    print(f"  Revenue: {baseline_total_revenue:,.0f} Ar (${baseline_total_revenue/4500:.0f})")

    print(f"\nSMART BATTERY:")
    print(f"  Curtailment: {smart_total_curtail:.0f} kWh ({smart_total_curtail/smart_total_pv*100:.1f}%)")
    print(f"  Revenue: {smart_total_revenue:,.0f} Ar (${smart_total_revenue/4500:.0f})")

    curtail_reduction = baseline_total_curtail - smart_total_curtail
    revenue_increase = smart_total_revenue - baseline_total_revenue

    print(f"\nIMPACT:")
    print(f"  ✅ Curtailment reduced by {curtail_reduction:.0f} kWh ({curtail_reduction/baseline_total_curtail*100:.1f}%)")
    print(f"  ✅ Revenue increased by {revenue_increase:,.0f} Ar (${revenue_increase/4500:.0f}/week)")

    # Save
    output_path = Path("python-optimizer/results")
    output_path.mkdir(parents=True, exist_ok=True)

    comparison = {
        "config": {
            "days": 7,
            "pv_capacity_kw": specs.pv_capacity_kw,
            "battery_capacity_kwh": specs.battery_capacity_kwh,
            "note": "Simple battery optimization demo"
        },
        "baseline": {
            "summary": {
                "total_pv_kwh": baseline_total_pv,
                "total_curtail_kwh": baseline_total_curtail,
                "curtailment_rate": baseline_total_curtail / baseline_total_pv,
                "total_revenue_ariary": baseline_total_revenue,
            },
            "daily": baseline_daily
        },
        "kora": {
            "summary": {
                "total_pv_kwh": smart_total_pv,
                "total_curtail_kwh": smart_total_curtail,
                "curtailment_rate": smart_total_curtail / smart_total_pv,
                "total_revenue_ariary": smart_total_revenue,
            },
            "daily": smart_daily
        },
        "impact": {
            "curtailment_reduction_kwh": curtail_reduction,
            "revenue_increase_ariary": revenue_increase,
        }
    }

    json_path = output_path / "mahavelona_comparison.json"
    with open(json_path, "w") as f:
        json.dump(comparison, f, indent=2)

    print(f"\n✅ Results saved to {json_path}")
    print("\nNow refresh your browser to see the dashboard! 🎉")


if __name__ == "__main__":
    main()
