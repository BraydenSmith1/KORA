"""
KORA Simulation Service

Runs closed-loop simulation with time acceleration for demos and testing.

Features:
- Real optimizer runs on simulated data
- Closed-loop battery SOC tracking (optimizer decisions affect state)
- Time acceleration (e.g., 1 real minute = 1 simulated hour)
- Real-time telemetry via API posts
- Persistent state in database
"""

from __future__ import annotations

import asyncio
import sys
import signal
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import requests

from .config import SiteConfig, load_config
from .service import OptimizerRunner
from .logging import get_logger, setup_logging

# Add parent directory to path for mahavelona_config
sys.path.insert(0, str(Path(__file__).parent.parent))
from mahavelona_config import (
    generate_madagascar_solar_profile,
    generate_madagascar_demand_profile,
    MahavelonaSpecs,
)

logger = get_logger(__name__)


@dataclass
class SimulationConfig:
    """Configuration for simulation mode."""

    # Time acceleration: how many simulated seconds per real second
    # 60 = 1 real second = 1 simulated minute
    # 3600 = 1 real second = 1 simulated hour
    time_acceleration: float = 60.0

    # How often to tick (real seconds)
    tick_interval_sec: float = 1.0

    # How often to run optimizer (simulated hours)
    optimizer_interval_hours: int = 1

    # Initial conditions
    initial_soc_pct: float = 45.0
    start_hour: int = 6  # 6am

    # API endpoint for posting telemetry
    api_url: str = "http://localhost:4000"

    # Site ID
    site_id: str = "mahavelona"


@dataclass
class SimulationState:
    """Current simulation state."""

    simulated_time: datetime = field(default_factory=datetime.now)
    battery_soc_kwh: float = 45.0
    battery_soc_pct: float = 45.0

    # Current values
    current_pv_kw: float = 0.0
    current_demand_kw: float = 0.0
    current_price_ariary: float = 1750.0
    current_charge_kw: float = 0.0
    current_curtail_kw: float = 0.0

    # Active optimizer schedule (if any)
    active_price_schedule: Optional[List[float]] = None
    active_battery_schedule: Optional[Dict[str, List[float]]] = None
    schedule_start_hour: int = 0

    # Totals
    total_energy_kwh: float = 0.0
    total_curtail_kwh: float = 0.0
    total_revenue_ar: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulatedTime": self.simulated_time.isoformat(),
            "batterySocKwh": self.battery_soc_kwh,
            "batterySocPct": self.battery_soc_pct,
            "currentPvKw": self.current_pv_kw,
            "currentDemandKw": self.current_demand_kw,
            "currentPriceAriary": self.current_price_ariary,
            "currentChargeKw": self.current_charge_kw,
            "currentCurtailKw": self.current_curtail_kw,
            "totalEnergyKwh": self.total_energy_kwh,
            "totalCurtailKwh": self.total_curtail_kwh,
            "totalRevenueAr": self.total_revenue_ar,
        }


class SimulationService:
    """
    Closed-loop simulation with time acceleration.

    Runs the real KORA optimizer on simulated data, with battery state
    tracking based on optimizer decisions.
    """

    def __init__(
        self,
        site_config: SiteConfig,
        sim_config: SimulationConfig,
    ):
        self.site_config = site_config
        self.sim_config = sim_config
        self.specs = MahavelonaSpecs()

        self.runner = OptimizerRunner(site_config)
        self.state = SimulationState()

        self._running = False
        self._paused = False
        self._last_optimizer_hour = -1

        # Pre-generate 24-hour profiles
        self._regenerate_profiles()

    def _regenerate_profiles(self, day_offset: int = 0) -> None:
        """Generate fresh 24-hour profiles."""
        # Vary conditions slightly each day
        np.random.seed(int(datetime.now().timestamp()) + day_offset)

        seasons = ["dry", "dry", "dry", "wet"]  # Weight towards dry season
        day_types = ["clear", "clear", "partly_cloudy"]

        season = np.random.choice(seasons)
        day_type = np.random.choice(day_types)

        self._pv_profile = generate_madagascar_solar_profile(
            peak_capacity_kw=self.specs.pv_capacity_kw,
            hours=24,
            season=season,
            day_type=day_type,
        )

        self._demand_profile = generate_madagascar_demand_profile(
            total_customers=self.specs.total_customers,
            peak_load_kw=53,
            hours=24,
            day_type="weekday",
        )

        logger.info(f"Generated profiles for {season} season, {day_type} day")

    def _get_current_values(self, hour: int) -> tuple[float, float]:
        """Get interpolated PV and demand for current simulated time."""
        # Get minute within hour for interpolation
        minute = self.state.simulated_time.minute
        fraction = minute / 60.0

        # Current and next hour values
        current_hour = hour % 24
        next_hour = (hour + 1) % 24

        pv_current = self._pv_profile[current_hour]
        pv_next = self._pv_profile[next_hour]
        pv = pv_current + (pv_next - pv_current) * fraction

        demand_current = self._demand_profile[current_hour]
        demand_next = self._demand_profile[next_hour]
        demand = demand_current + (demand_next - demand_current) * fraction

        # Add small noise
        pv *= np.random.uniform(0.98, 1.02)
        demand *= np.random.uniform(0.97, 1.03)

        return max(0, pv), max(0, demand)

    def _get_schedule_values(self, hour: int) -> tuple[float, float, float]:
        """Get price and battery commands from active schedule."""
        if self.state.active_price_schedule is None:
            # No schedule yet - use baseline values
            return 1750.0, 0.0, 0.0

        # Find index in schedule
        schedule_idx = (hour - self.state.schedule_start_hour) % 24
        if schedule_idx < 0:
            schedule_idx += 24

        if schedule_idx >= len(self.state.active_price_schedule):
            return 1750.0, 0.0, 0.0

        price = self.state.active_price_schedule[schedule_idx]

        charge_kw = 0.0
        discharge_kw = 0.0
        if self.state.active_battery_schedule:
            charge_kw = self.state.active_battery_schedule.get("charge_kw", [])[schedule_idx] if schedule_idx < len(self.state.active_battery_schedule.get("charge_kw", [])) else 0.0
            discharge_kw = self.state.active_battery_schedule.get("discharge_kw", [])[schedule_idx] if schedule_idx < len(self.state.active_battery_schedule.get("discharge_kw", [])) else 0.0

        return price, charge_kw, discharge_kw

    def _update_battery(self, charge_kw: float, discharge_kw: float, dt_hours: float) -> None:
        """Update battery SOC based on charge/discharge command."""
        eta_charge = self.specs.battery_efficiency_charge
        eta_discharge = self.specs.battery_efficiency_discharge

        # Net energy change
        energy_in = charge_kw * eta_charge * dt_hours
        energy_out = discharge_kw / eta_discharge * dt_hours

        new_soc = self.state.battery_soc_kwh + energy_in - energy_out

        # Clamp to physical limits
        soc_min = self.specs.battery_capacity_kwh * (self.specs.soc_min_percent / 100)
        soc_max = self.specs.battery_capacity_kwh * (self.specs.soc_max_percent / 100)

        self.state.battery_soc_kwh = np.clip(new_soc, soc_min, soc_max)
        self.state.battery_soc_pct = (self.state.battery_soc_kwh / self.specs.battery_capacity_kwh) * 100

    def _calculate_curtailment(self, pv_kw: float, demand_kw: float, charge_kw: float) -> float:
        """Calculate curtailment given current conditions."""
        # Excess solar after serving demand and charging battery
        excess = pv_kw - demand_kw - charge_kw
        return max(0, excess)

    async def _run_optimizer(self) -> None:
        """Run optimizer for next 24 hours."""
        hour = self.state.simulated_time.hour

        logger.info(f"Running optimizer at simulated hour {hour:02d}:00")

        # Get 24-hour forecasts starting from current hour
        pv_forecast = []
        demand_forecast = []

        for h in range(24):
            idx = (hour + h) % 24
            pv_forecast.append(float(self._pv_profile[idx]))
            demand_forecast.append(float(self._demand_profile[idx]))

        # Run optimization
        result = self.runner.run(
            pv_forecast=pv_forecast,
            demand_forecast=demand_forecast,
            initial_soc_kwh=self.state.battery_soc_kwh,
        )

        if result.is_success:
            # Store new schedule
            self.state.active_price_schedule = result.price_schedule
            self.state.active_battery_schedule = result.battery_schedule
            self.state.schedule_start_hour = hour

            logger.info(
                f"Optimizer success: curtailment={result.curtailment_rate*100:.1f}%, "
                f"revenue={result.total_revenue:.0f} Ar"
            )

            # Post result to API
            await self._post_optimizer_result(result, pv_forecast, demand_forecast)
        else:
            logger.error(f"Optimizer failed: {result.error_message}")

    def _to_json_safe(self, val):
        """Convert numpy arrays and handle NaN/Inf for JSON serialization."""
        import numpy as np
        if val is None:
            return None
        if isinstance(val, np.ndarray):
            val = val.tolist()
        if isinstance(val, list):
            return [self._to_json_safe(v) for v in val]
        if isinstance(val, dict):
            return {k: self._to_json_safe(v) for k, v in val.items()}
        if isinstance(val, float):
            if np.isnan(val) or np.isinf(val):
                return None
            return float(val)
        if isinstance(val, (np.floating, np.integer)):
            return float(val)
        return val

    async def _post_optimizer_result(
        self,
        result,
        pv_forecast: List[float],
        demand_forecast: List[float],
    ) -> None:
        """Post optimizer result to API."""
        try:
            data = {
                "siteId": self.sim_config.site_id,
                "runId": result.run_id,
                "simulatedTime": self.state.simulated_time.isoformat(),
                "status": result.status,
                "solver": self.site_config.optimizer.solver,
                "solveTimeSec": self._to_json_safe(result.solve_time_sec),
                "curtailmentRate": self._to_json_safe(result.curtailment_rate),
                "totalRevenueAriary": self._to_json_safe(result.total_revenue),
                "totalCurtailmentKwh": self._to_json_safe(result.total_curtailment_kwh),
                "totalDemandServedKwh": self._to_json_safe(result.total_demand_served_kwh),
                "blackoutHours": result.blackout_hours or 0,
                "priceSchedule": self._to_json_safe(result.price_schedule),
                "batterySchedule": self._to_json_safe(result.battery_schedule),
                "pvForecast": self._to_json_safe(pv_forecast),
                "demandForecast": self._to_json_safe(demand_forecast),
                "errorMessage": result.error_message,
            }

            response = requests.post(
                f"{self.sim_config.api_url}/api/optimizer/result",
                json=data,
                timeout=5,
            )
            response.raise_for_status()
            logger.debug("Posted optimizer result to API")
        except Exception as e:
            logger.error(f"Failed to post optimizer result: {e}")

    async def _post_tick(self) -> None:
        """Post telemetry tick to API."""
        try:
            data = {
                "siteId": self.sim_config.site_id,
                "simulatedTime": self.state.simulated_time.isoformat(),
                "pvKw": self.state.current_pv_kw,
                "demandKw": self.state.current_demand_kw,
                "priceAriary": self.state.current_price_ariary,
                "socKwh": self.state.battery_soc_kwh,
                "socPct": self.state.battery_soc_pct,
                "chargeKw": self.state.current_charge_kw,
                "curtailKw": self.state.current_curtail_kw,
                "totalEnergyKwh": self.state.total_energy_kwh,
                "totalCurtailKwh": self.state.total_curtail_kwh,
                "totalRevenueAr": self.state.total_revenue_ar,
            }

            response = requests.post(
                f"{self.sim_config.api_url}/api/simulation/tick",
                json=data,
                timeout=2,
            )
            response.raise_for_status()
        except Exception as e:
            logger.debug(f"Failed to post tick: {e}")

    async def _tick(self) -> None:
        """Execute one simulation tick."""
        hour = self.state.simulated_time.hour

        # Get current PV and demand
        pv, demand = self._get_current_values(hour)
        self.state.current_pv_kw = pv
        self.state.current_demand_kw = demand

        # Get schedule values
        price, charge_cmd, discharge_cmd = self._get_schedule_values(hour)
        self.state.current_price_ariary = price

        # Calculate actual charge/discharge based on availability
        # Can only charge if there's excess solar
        excess_solar = pv - demand
        actual_charge = min(charge_cmd, max(0, excess_solar), self.specs.battery_power_kw)

        # Can only discharge if there's demand deficit
        deficit = demand - pv
        actual_discharge = min(discharge_cmd, max(0, deficit), self.specs.battery_power_kw)

        self.state.current_charge_kw = actual_charge - actual_discharge

        # Calculate curtailment
        curtail = self._calculate_curtailment(pv, demand, actual_charge)
        self.state.current_curtail_kw = curtail

        # Time step in hours
        dt_hours = (self.sim_config.time_acceleration * self.sim_config.tick_interval_sec) / 3600.0

        # Update battery SOC
        self._update_battery(actual_charge, actual_discharge, dt_hours)

        # Update totals
        self.state.total_energy_kwh += demand * dt_hours
        self.state.total_curtail_kwh += curtail * dt_hours
        self.state.total_revenue_ar += demand * price * dt_hours

        # Post telemetry to API
        await self._post_tick()

        # Check if we need to run optimizer (new hour)
        if hour != self._last_optimizer_hour:
            if hour % self.sim_config.optimizer_interval_hours == 0:
                await self._run_optimizer()
            self._last_optimizer_hour = hour

        # Advance simulated time
        delta_seconds = self.sim_config.time_acceleration * self.sim_config.tick_interval_sec
        self.state.simulated_time += timedelta(seconds=delta_seconds)

        # Check if we crossed into a new day
        if self.state.simulated_time.hour == 0 and self._last_optimizer_hour == 23:
            self._regenerate_profiles()

    async def _check_api_state(self) -> None:
        """Check API for pause/stop commands."""
        try:
            response = requests.get(
                f"{self.sim_config.api_url}/api/optimizer/status",
                params={"siteId": self.sim_config.site_id},
                timeout=2,
            )
            if response.ok:
                data = response.json()
                sim = data.get("simulation", {})
                if not sim.get("isRunning", True):
                    self._running = False
                self._paused = sim.get("isPaused", False)
        except Exception:
            pass  # Ignore errors, keep running

    async def run(self) -> None:
        """Run simulation loop."""
        self._running = True

        # Initialize state
        now = datetime.now()
        self.state.simulated_time = now.replace(
            hour=self.sim_config.start_hour,
            minute=0,
            second=0,
            microsecond=0,
        )

        # Initialize battery SOC
        self.state.battery_soc_kwh = (
            self.sim_config.initial_soc_pct / 100
        ) * self.specs.battery_capacity_kwh
        self.state.battery_soc_pct = self.sim_config.initial_soc_pct

        logger.info(
            f"Starting simulation at {self.state.simulated_time.strftime('%H:%M')}, "
            f"SOC={self.state.battery_soc_pct:.1f}%, "
            f"acceleration={self.sim_config.time_acceleration}x"
        )

        # Run initial optimizer
        await self._run_optimizer()

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.stop)

        check_interval = 5  # Check API every 5 ticks
        tick_count = 0

        try:
            while self._running:
                if not self._paused:
                    await self._tick()

                    # Log every simulated hour
                    if self.state.simulated_time.minute == 0 and self.state.simulated_time.second == 0:
                        logger.info(
                            f"[{self.state.simulated_time.strftime('%H:%M')}] "
                            f"PV={self.state.current_pv_kw:.1f}kW, "
                            f"Demand={self.state.current_demand_kw:.1f}kW, "
                            f"SOC={self.state.battery_soc_pct:.1f}%, "
                            f"Curtail={self.state.current_curtail_kw:.1f}kW"
                        )

                # Check API state periodically
                tick_count += 1
                if tick_count >= check_interval:
                    await self._check_api_state()
                    tick_count = 0

                await asyncio.sleep(self.sim_config.tick_interval_sec)

        except asyncio.CancelledError:
            logger.info("Simulation cancelled")
        finally:
            self._running = False
            logger.info("Simulation stopped")

    def stop(self) -> None:
        """Stop simulation."""
        logger.info("Stopping simulation...")
        self._running = False


def main():
    """Main entry point for simulation mode."""
    import argparse

    parser = argparse.ArgumentParser(description="KORA Simulation Service")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to site configuration YAML file",
    )
    parser.add_argument(
        "--time-acceleration", "-t",
        type=float,
        default=60.0,
        help="Time acceleration factor (default: 60 = 1 sec real = 1 min sim)",
    )
    parser.add_argument(
        "--start-hour",
        type=int,
        default=6,
        help="Starting hour of day (default: 6)",
    )
    parser.add_argument(
        "--initial-soc",
        type=float,
        default=45.0,
        help="Initial battery SOC percentage (default: 45)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:4000",
        help="API URL for posting telemetry",
    )
    parser.add_argument(
        "--site-id",
        type=str,
        default="mahavelona",
        help="Site ID",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=args.log_level)

    # Load site configuration
    try:
        site_config = load_config(args.config)
        logger.info(f"Loaded site config: {site_config.site_name}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Create simulation config
    sim_config = SimulationConfig(
        time_acceleration=args.time_acceleration,
        start_hour=args.start_hour,
        initial_soc_pct=args.initial_soc,
        api_url=args.api_url,
        site_id=args.site_id,
    )

    # Create and run simulation
    service = SimulationService(site_config, sim_config)
    asyncio.run(service.run())


if __name__ == "__main__":
    main()
