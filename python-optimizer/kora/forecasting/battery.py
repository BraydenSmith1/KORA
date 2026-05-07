"""
Battery State of Charge (SoC) projector.

Projects battery state over time given:
- Current SoC
- PV forecast
- Demand forecast
- Planned charge/discharge schedule (optional)

Uses physics-based model with efficiency losses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import SiteConfig

logger = logging.getLogger(__name__)


@dataclass
class SoCProjection:
    """Battery state of charge projection result."""

    site_id: str
    projection_time: datetime
    initial_soc_kwh: float

    # Time series (length = horizon + 1, includes initial state)
    hours: List[int]           # Hour indices [0, 1, 2, ...]
    soc_kwh: List[float]       # SoC at each hour
    soc_percent: List[float]   # SoC as percentage

    # Actions (length = horizon)
    charge_kw: List[float]     # Charge power each hour
    discharge_kw: List[float]  # Discharge power each hour

    # Warnings and constraints
    warnings: List[str] = field(default_factory=list)
    min_soc_reached: bool = False
    max_soc_reached: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "site_id": self.site_id,
            "projection_time": self.projection_time.isoformat(),
            "initial_soc_kwh": self.initial_soc_kwh,
            "hours": self.hours,
            "soc_kwh": self.soc_kwh,
            "soc_percent": self.soc_percent,
            "charge_kw": self.charge_kw,
            "discharge_kw": self.discharge_kw,
            "warnings": self.warnings,
            "min_soc_reached": self.min_soc_reached,
            "max_soc_reached": self.max_soc_reached,
        }


class SoCProjector:
    """
    Battery State of Charge projector.

    Projects SoC over time given forecasts and optionally a dispatch schedule.
    If no schedule is provided, assumes battery follows simple rules:
    - Charge during solar surplus
    - Discharge during demand deficit

    Usage:
        projector = SoCProjector(
            capacity_kwh=115,
            power_kw=54,
            soc_min_pct=20,
            soc_max_pct=95
        )
        projection = projector.project(
            initial_soc_kwh=50,
            pv_forecast=[0, 0, 20, 80, 100, ...],
            demand_forecast=[10, 8, 15, 25, 30, ...]
        )
    """

    def __init__(
        self,
        capacity_kwh: float = 115.0,
        power_kw: float = 54.0,
        soc_min_pct: float = 20.0,
        soc_max_pct: float = 95.0,
        eta_charge: float = 0.94,
        eta_discharge: float = 0.94,
        site_id: str = "default",
    ):
        """
        Initialize SoC projector.

        Args:
            capacity_kwh: Battery capacity in kWh
            power_kw: Maximum charge/discharge power in kW
            soc_min_pct: Minimum allowed SoC (%)
            soc_max_pct: Maximum allowed SoC (%)
            eta_charge: Charging efficiency (0-1)
            eta_discharge: Discharging efficiency (0-1)
            site_id: Site identifier
        """
        self.capacity_kwh = capacity_kwh
        self.power_kw = power_kw
        self.soc_min_kwh = capacity_kwh * soc_min_pct / 100
        self.soc_max_kwh = capacity_kwh * soc_max_pct / 100
        self.soc_min_pct = soc_min_pct
        self.soc_max_pct = soc_max_pct
        self.eta_charge = eta_charge
        self.eta_discharge = eta_discharge
        self.site_id = site_id

    @classmethod
    def from_config(cls, config: "SiteConfig") -> "SoCProjector":
        """Create projector from site configuration."""
        return cls(
            capacity_kwh=config.battery.capacity_kwh,
            power_kw=config.battery.power_kw,
            soc_min_pct=config.battery.soc_min_percent,
            soc_max_pct=config.battery.soc_max_percent,
            eta_charge=config.battery.efficiency_charge,
            eta_discharge=config.battery.efficiency_discharge,
            site_id=config.site_id,
        )

    def project(
        self,
        initial_soc_kwh: float,
        pv_forecast: List[float],
        demand_forecast: List[float],
        charge_schedule: Optional[List[float]] = None,
        discharge_schedule: Optional[List[float]] = None,
    ) -> SoCProjection:
        """
        Project SoC over forecast horizon.

        If charge/discharge schedules are not provided, the projector
        assumes the battery will:
        1. Charge with excess solar (PV > demand)
        2. Discharge to meet demand deficit (demand > PV)

        Args:
            initial_soc_kwh: Starting battery state in kWh
            pv_forecast: Hourly PV production forecast (kW)
            demand_forecast: Hourly demand forecast (kW)
            charge_schedule: Optional planned charge power (kW)
            discharge_schedule: Optional planned discharge power (kW)

        Returns:
            SoCProjection with hour-by-hour battery state
        """
        hours = len(pv_forecast)
        if len(demand_forecast) != hours:
            raise ValueError("PV and demand forecasts must have same length")

        # Initialize outputs
        soc_kwh = [initial_soc_kwh]
        soc_percent = [initial_soc_kwh / self.capacity_kwh * 100]
        charge_kw = []
        discharge_kw = []
        warnings = []

        current_soc = initial_soc_kwh
        min_soc_reached = False
        max_soc_reached = False

        for h in range(hours):
            pv = pv_forecast[h]
            demand = demand_forecast[h]

            # Determine charge/discharge action
            if charge_schedule is not None and discharge_schedule is not None:
                # Use provided schedule
                charge = charge_schedule[h] if h < len(charge_schedule) else 0
                discharge = discharge_schedule[h] if h < len(discharge_schedule) else 0
            else:
                # Auto-calculate based on energy balance
                charge, discharge = self._auto_dispatch(pv, demand, current_soc)

            # Apply power limits
            charge = min(charge, self.power_kw)
            discharge = min(discharge, self.power_kw)

            # Calculate energy change
            # Charging: only eta_charge of grid energy goes into battery
            # Discharging: battery loses energy but only eta_discharge goes to grid
            energy_in = charge * self.eta_charge  # kWh stored
            energy_out = discharge / self.eta_discharge  # kWh removed from battery

            new_soc = current_soc + energy_in - energy_out

            # Check and enforce constraints
            if new_soc > self.soc_max_kwh:
                excess = new_soc - self.soc_max_kwh
                warnings.append(f"Hour {h}: SoC would exceed max by {excess:.1f} kWh")
                new_soc = self.soc_max_kwh
                max_soc_reached = True

            if new_soc < self.soc_min_kwh:
                deficit = self.soc_min_kwh - new_soc
                warnings.append(f"Hour {h}: SoC would drop below min by {deficit:.1f} kWh")
                new_soc = self.soc_min_kwh
                min_soc_reached = True

            # Update state
            current_soc = new_soc
            soc_kwh.append(round(current_soc, 2))
            soc_percent.append(round(current_soc / self.capacity_kwh * 100, 1))
            charge_kw.append(round(charge, 2))
            discharge_kw.append(round(discharge, 2))

        return SoCProjection(
            site_id=self.site_id,
            projection_time=datetime.utcnow(),
            initial_soc_kwh=initial_soc_kwh,
            hours=list(range(hours + 1)),
            soc_kwh=soc_kwh,
            soc_percent=soc_percent,
            charge_kw=charge_kw,
            discharge_kw=discharge_kw,
            warnings=warnings,
            min_soc_reached=min_soc_reached,
            max_soc_reached=max_soc_reached,
        )

    def _auto_dispatch(
        self,
        pv: float,
        demand: float,
        current_soc: float,
    ) -> tuple[float, float]:
        """
        Calculate automatic charge/discharge based on energy balance.

        Simple rule:
        - If PV > demand: charge battery with excess
        - If demand > PV: discharge battery to meet deficit

        Args:
            pv: PV production (kW)
            demand: Load demand (kW)
            current_soc: Current SoC (kWh)

        Returns:
            Tuple of (charge_kw, discharge_kw)
        """
        if pv > demand:
            # Excess solar - charge battery
            excess = pv - demand
            # Limit by power rating and available capacity
            max_charge = min(
                excess,
                self.power_kw,
                (self.soc_max_kwh - current_soc) / self.eta_charge
            )
            return max(0, max_charge), 0.0
        else:
            # Deficit - discharge battery
            deficit = demand - pv
            # Limit by power rating and available energy
            max_discharge = min(
                deficit,
                self.power_kw,
                (current_soc - self.soc_min_kwh) * self.eta_discharge
            )
            return 0.0, max(0, max_discharge)

    def get_hours_below_threshold(
        self,
        projection: SoCProjection,
        threshold_pct: float = 25.0,
    ) -> int:
        """Count hours where SoC is below threshold."""
        return sum(1 for soc in projection.soc_percent if soc < threshold_pct)

    def get_available_energy(self, current_soc_kwh: float) -> float:
        """Calculate usable energy above minimum SoC."""
        return max(0, current_soc_kwh - self.soc_min_kwh) * self.eta_discharge

    def get_available_capacity(self, current_soc_kwh: float) -> float:
        """Calculate available charging capacity."""
        return max(0, self.soc_max_kwh - current_soc_kwh) / self.eta_charge
