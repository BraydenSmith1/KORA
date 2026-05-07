"""
Mahavelona Microgrid Configuration (Africa GreenTec, Madagascar)

Real specs from the pilot site:
- Location: Mahavelona, Itasy region, Madagascar
- Solar: 118.5 kWp (300 × TrinaSolar 395W panels)
- Battery: 115 kWh (24 × TESVOLT 4.8 kWh modules)
- Inverter: 100 kW (2 × 50 kW SMA)
- Customers: 251 connections (201 households, 34 SMEs, 16 public)
- Daily production: ~548 kWh/day average
- Peak load: 53 kW (evening harvest period)
- Current curtailment: >70% (battery full by 10am!)
"""

import numpy as np
from typing import Tuple, List
from dataclasses import dataclass


@dataclass
class MahavelonaSpecs:
    """Physical specifications of the Mahavelona microgrid"""

    # Solar array
    pv_capacity_kw: float = 118.5
    daily_production_kwh: float = 548  # Average (January estimate)

    # Battery storage
    battery_capacity_kwh: float = 115
    battery_power_kw: float = 54  # Available reserve power
    battery_efficiency_charge: float = 0.94
    battery_efficiency_discharge: float = 0.94
    soc_min_percent: float = 20  # Don't discharge below 20%
    soc_max_percent: float = 95  # Don't charge above 95% (battery health)

    # Grid/inverter limits
    inverter_capacity_kw: float = 100

    # Customer base
    total_customers: int = 251
    households: int = 201
    smes: int = 34
    public_institutions: int = 16

    # Current performance (BASELINE - what we're fixing!)
    baseline_curtailment_rate: float = 0.70  # 70% curtailment!
    battery_full_by_hour: int = 10  # 10am battery is full, rest curtailed


@dataclass
class MahavelonaFareStructure:
    """Current time-of-use pricing (Ariary/kWh)"""

    # Time windows
    peak_start: int = 17  # 5pm
    peak_end: int = 23    # 11pm
    intermediate_start: int = 8  # 8am
    intermediate_end: int = 17   # 5pm (actually 4:59pm)
    # Off-peak: 11pm-8am (remaining hours)

    # Customer categories (Ariary/kWh)
    # Format: (peak, intermediate, off_peak)
    T1_T2_household = (1850, 1700, 1850)  # Low/medium household
    T3_household = (1900, 1700, 1900)     # High household
    T4_sme_public = (1950, 1800, 1950)    # SMEs and public institutions
    T5_heavy = (2000, 1900, 2000)         # Heavy equipment (shelling, welding)

    # Fixed monthly fees (Ariary)
    fixed_fee_T1_T2 = 10000
    fixed_fee_T3 = 15000
    fixed_fee_T4 = 15000
    fixed_fee_T5 = 20000  # Average of 18k-20k

    # Weighted average price (assuming customer mix)
    @property
    def avg_peak_price(self) -> float:
        """Weighted average peak price across customer types"""
        return 0.6 * self.T1_T2_household[0] + 0.3 * self.T4_sme_public[0] + 0.1 * self.T5_heavy[0]

    @property
    def avg_intermediate_price(self) -> float:
        """Weighted average intermediate price"""
        return 0.6 * self.T1_T2_household[1] + 0.3 * self.T4_sme_public[1] + 0.1 * self.T5_heavy[1]

    @property
    def avg_offpeak_price(self) -> float:
        """Weighted average off-peak price"""
        return 0.6 * self.T1_T2_household[2] + 0.3 * self.T4_sme_public[2] + 0.1 * self.T5_heavy[2]


def generate_madagascar_solar_profile(
    peak_capacity_kw: float = 118.5,
    hours: int = 24,
    season: str = "dry",  # "dry" or "wet"
    day_type: str = "clear"  # "clear", "partly_cloudy", "cloudy"
) -> np.ndarray:
    """
    Generate realistic solar production profile for Madagascar.

    Madagascar is in Southern Hemisphere:
    - Dry season (Apr-Oct): Strong sun, minimal clouds, peak production
    - Wet season (Nov-Mar): More clouds, rain, reduced production

    Sunrise: ~6am, Sunset: ~6pm (varies slightly by season)
    Peak sun: 11am-1pm
    """
    solar = np.zeros(hours)

    # Season multipliers
    season_multiplier = 1.0 if season == "dry" else 0.75

    # Day type cloud cover
    cloud_factors = {
        "clear": 1.0,
        "partly_cloudy": 0.7,
        "cloudy": 0.3
    }
    cloud_multiplier = cloud_factors.get(day_type, 1.0)

    for h in range(hours):
        # Sunrise at 6am (hour 6), sunset at 6pm (hour 18)
        if 6 <= h <= 18:
            # Use sine curve for solar path
            # Peak at noon (hour 12)
            angle = (h - 6) / 12 * np.pi  # 0 to π over 12 hours
            base_output = np.sin(angle)

            # Apply atmospheric effects (sun angle)
            # Morning/evening have more atmospheric absorption
            if h < 9 or h > 15:
                atmospheric_factor = 0.85
            else:
                atmospheric_factor = 1.0

            # Random variability (clouds passing, etc.)
            noise = np.random.normal(1.0, 0.05)  # ±5% variability

            solar[h] = (
                peak_capacity_kw
                * base_output
                * atmospheric_factor
                * season_multiplier
                * cloud_multiplier
                * noise
            )

            # Clamp to physical limits
            solar[h] = np.clip(solar[h], 0, peak_capacity_kw)

    return solar


def generate_madagascar_demand_profile(
    total_customers: int = 251,
    peak_load_kw: float = 53,
    hours: int = 24,
    day_type: str = "weekday",  # "weekday" or "weekend"
    price_elasticity: float = 0.0  # For baseline, no price response
) -> np.ndarray:
    """
    Generate realistic customer demand profile for rural Madagascar microgrid.

    Typical patterns:
    - Early morning (5-7am): Low (people waking up, phone charging)
    - Morning (8am-12pm): Medium (SMEs starting, schools, clinics)
    - Midday (12-2pm): Low-medium (lunch, siesta)
    - Afternoon (2-5pm): Medium (SMEs active, schools)
    - Evening peak (6-9pm): HIGH (cooking, lighting, entertainment, phone charging)
    - Night (10pm-5am): Low (minimal activity)
    """
    demand = np.zeros(hours)

    # Base load (always-on: fridges, minimal lighting, etc.)
    base_load_kw = peak_load_kw * 0.15  # ~8 kW

    # Hourly patterns (normalized 0-1)
    hourly_pattern = {
        0: 0.20,   # Midnight
        1: 0.15,   # 1am
        2: 0.15,
        3: 0.15,
        4: 0.15,
        5: 0.20,   # 5am - early risers
        6: 0.35,   # 6am - morning activity
        7: 0.45,   # 7am
        8: 0.50,   # 8am - SMEs open, schools start
        9: 0.48,
        10: 0.45,
        11: 0.50,
        12: 0.40,  # Noon - lunch break
        13: 0.38,
        14: 0.45,  # Afternoon
        15: 0.50,
        16: 0.60,  # Late afternoon - SMEs peak
        17: 0.75,  # 5pm - transitioning to evening
        18: 0.95,  # 6pm - PEAK (cooking starts, lighting)
        19: 1.00,  # 7pm - PEAK (dinner, entertainment)
        20: 0.90,  # 8pm - Still high
        21: 0.70,  # 9pm - Winding down
        22: 0.50,  # 10pm
        23: 0.30,  # 11pm
    }

    # Weekend adjustment (lower SME activity, higher household)
    weekend_factor = 0.85 if day_type == "weekend" else 1.0

    for h in range(hours):
        pattern_value = hourly_pattern.get(h, 0.3)

        # Add randomness (customer behavior variability)
        noise = np.random.normal(1.0, 0.1)  # ±10% variability

        demand[h] = (
            base_load_kw
            + (peak_load_kw - base_load_kw) * pattern_value * weekend_factor * noise
        )

        # Clamp to reasonable bounds
        demand[h] = np.clip(demand[h], base_load_kw, peak_load_kw * 1.1)

    return demand


def generate_baseline_scenario(
    specs: MahavelonaSpecs,
    hours: int = 24,
    season: str = "dry",
    day_type: str = "clear"
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate a baseline scenario showing CURRENT performance (70% curtailment).

    Returns:
        solar_kw: Hourly solar production
        demand_kw: Hourly customer demand
        curtailment_kw: Hourly curtailment (what we want to eliminate!)
    """
    solar = generate_madagascar_solar_profile(
        peak_capacity_kw=specs.pv_capacity_kw,
        hours=hours,
        season=season,
        day_type=day_type
    )

    demand = generate_madagascar_demand_profile(
        total_customers=specs.total_customers,
        peak_load_kw=53,  # Known peak load
        hours=hours,
        day_type="weekday"
    )

    # Simulate CURRENT behavior (battery fills by 10am, then curtailment)
    curtailment = np.zeros(hours)
    battery_soc = specs.battery_capacity_kwh * 0.3  # Start at 30%

    for h in range(hours):
        available_solar = solar[h]
        customer_demand = demand[h]

        # How much battery can absorb this hour?
        battery_headroom = specs.battery_capacity_kwh * 0.95 - battery_soc
        max_charge_this_hour = min(
            battery_headroom,
            specs.battery_power_kw,  # Power limit
            available_solar - customer_demand  # Excess after serving demand
        )

        if available_solar > customer_demand:
            # Excess solar
            excess = available_solar - customer_demand

            if max_charge_this_hour > 0:
                # Charge battery
                actual_charge = min(excess, max_charge_this_hour)
                battery_soc += actual_charge * specs.battery_efficiency_charge
                curtailment[h] = excess - actual_charge
            else:
                # Battery full! All excess is curtailed
                curtailment[h] = excess
        else:
            # Deficit - discharge battery
            deficit = customer_demand - available_solar
            max_discharge = min(
                battery_soc - specs.battery_capacity_kwh * 0.2,  # Don't go below 20%
                specs.battery_power_kw,
                deficit
            )
            if max_discharge > 0:
                battery_soc -= max_discharge / specs.battery_efficiency_discharge

    return solar, demand, curtailment


def generate_kora_optimized_demand(
    baseline_demand: np.ndarray,
    price_schedule: np.ndarray,
    reference_price: float = 1750,  # Ariary/kWh (baseline avg)
    elasticity: float = 0.6
) -> np.ndarray:
    """
    Apply price elasticity to shift demand.

    Elasticity = 0.6 means:
    - 10% price decrease → 6% demand increase
    - 20% price decrease → 12% demand increase

    Example: If price drops from 1750 to 1225 Ar (30% decrease),
             demand increases by 18% (0.6 × 30%)
    """
    optimized_demand = np.zeros_like(baseline_demand)

    for h in range(len(baseline_demand)):
        price_change_pct = (price_schedule[h] - reference_price) / reference_price
        demand_change_pct = -elasticity * price_change_pct  # Negative: lower price → higher demand

        optimized_demand[h] = baseline_demand[h] * (1 + demand_change_pct)

        # Clamp to reasonable bounds (demand can't go negative or >2× baseline)
        optimized_demand[h] = np.clip(
            optimized_demand[h],
            baseline_demand[h] * 0.5,  # Min 50% of baseline
            baseline_demand[h] * 2.0   # Max 2× baseline
        )

    return optimized_demand


if __name__ == "__main__":
    """Test the data generation"""
    specs = MahavelonaSpecs()
    fares = MahavelonaFareStructure()

    print("=== Mahavelona Microgrid Configuration ===")
    print(f"Solar capacity: {specs.pv_capacity_kw} kWp")
    print(f"Battery capacity: {specs.battery_capacity_kwh} kWh")
    print(f"Daily production: {specs.daily_production_kwh} kWh/day")
    print(f"Baseline curtailment: {specs.baseline_curtailment_rate * 100}%")
    print(f"Peak load: 53 kW")
    print()

    print("=== Current Pricing (Ariary/kWh) ===")
    print(f"Peak (5pm-11pm): {fares.avg_peak_price:.0f} Ar")
    print(f"Intermediate (8am-5pm): {fares.avg_intermediate_price:.0f} Ar")
    print(f"Off-peak (11pm-8am): {fares.avg_offpeak_price:.0f} Ar")
    print()

    # Generate sample day
    solar, demand, curtailment = generate_baseline_scenario(specs)

    daily_production = solar.sum()
    daily_demand = demand.sum()
    daily_curtailment = curtailment.sum()

    print("=== Sample Day (Baseline) ===")
    print(f"Solar production: {daily_production:.1f} kWh")
    print(f"Customer demand: {daily_demand:.1f} kWh")
    print(f"Curtailment: {daily_curtailment:.1f} kWh ({daily_curtailment/daily_production*100:.1f}%)")
    print()

    print("Sample hours:")
    for h in [6, 10, 12, 14, 18, 20]:
        print(f"  {h:02d}:00 - Solar: {solar[h]:5.1f} kW, Demand: {demand[h]:5.1f} kW, Curtail: {curtailment[h]:5.1f} kW")
