"""
Outage risk calculator.

Assesses risk of grid outages based on:
- Battery SoC projections
- Supply/demand balance
- Weather conditions

Provides early warning for operators.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .battery import SoCProjection

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """Outage risk assessment result."""

    site_id: str
    assessment_time: datetime

    # Risk scores (0-1, higher = more risk)
    overall_risk: float      # Weighted combination
    soc_risk: float          # Battery depletion risk
    demand_risk: float       # Demand exceeding supply risk
    weather_risk: float      # Severe weather impact risk

    # Risk factors
    peak_deficit_kw: float   # Maximum expected supply shortfall
    low_soc_hours: int       # Hours below 25% SoC
    critical_soc_hours: int  # Hours below 20% SoC (minimum)

    # Alert level and recommendations
    alert_level: str         # "normal", "watch", "warning", "critical"
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "site_id": self.site_id,
            "assessment_time": self.assessment_time.isoformat(),
            "overall_risk": self.overall_risk,
            "soc_risk": self.soc_risk,
            "demand_risk": self.demand_risk,
            "weather_risk": self.weather_risk,
            "peak_deficit_kw": self.peak_deficit_kw,
            "low_soc_hours": self.low_soc_hours,
            "critical_soc_hours": self.critical_soc_hours,
            "alert_level": self.alert_level,
            "recommendations": self.recommendations,
        }


class OutageRiskCalculator:
    """
    Calculates outage risk based on forecasts and current state.

    Risk factors:
    1. SoC depletion risk: Will battery reach minimum threshold?
    2. Demand risk: Peak demand exceeding available supply?
    3. Weather risk: Severe weather affecting PV or equipment?

    Usage:
        calculator = OutageRiskCalculator(
            battery_capacity_kwh=115,
            battery_power_kw=54,
            peak_demand_kw=53
        )
        risk = calculator.assess(
            soc_projection=projection,
            pv_forecast=[...],
            demand_forecast=[...]
        )
        print(f"Alert: {risk.alert_level}")
        for rec in risk.recommendations:
            print(f"  - {rec}")
    """

    # Risk thresholds
    LOW_SOC_THRESHOLD_PCT = 25.0      # SoC below this triggers warning
    CRITICAL_SOC_THRESHOLD_PCT = 20.0  # SoC below this triggers critical
    SUPPLY_DEFICIT_THRESHOLD = 0.1     # 10% of peak demand

    # Alert thresholds
    WATCH_RISK = 0.3
    WARNING_RISK = 0.5
    CRITICAL_RISK = 0.7

    def __init__(
        self,
        battery_capacity_kwh: float = 115.0,
        battery_power_kw: float = 54.0,
        peak_demand_kw: float = 53.0,
        site_id: str = "default",
    ):
        """
        Initialize risk calculator.

        Args:
            battery_capacity_kwh: Battery capacity
            battery_power_kw: Max charge/discharge power
            peak_demand_kw: Expected peak demand
            site_id: Site identifier
        """
        self.battery_capacity_kwh = battery_capacity_kwh
        self.battery_power_kw = battery_power_kw
        self.peak_demand_kw = peak_demand_kw
        self.site_id = site_id

    def assess(
        self,
        soc_projection: SoCProjection,
        pv_forecast: List[float],
        demand_forecast: List[float],
        weather_severe: bool = False,
        precipitation_mm: float = 0,
    ) -> RiskAssessment:
        """
        Calculate comprehensive risk assessment.

        Args:
            soc_projection: Battery SoC projection
            pv_forecast: Hourly PV production forecast (kW)
            demand_forecast: Hourly demand forecast (kW)
            weather_severe: Flag for severe weather conditions
            precipitation_mm: Expected precipitation (affects equipment)

        Returns:
            RiskAssessment with scores and recommendations
        """
        # Calculate SoC risk
        low_soc_hours = sum(
            1 for soc_pct in soc_projection.soc_percent
            if soc_pct < self.LOW_SOC_THRESHOLD_PCT
        )
        critical_soc_hours = sum(
            1 for soc_pct in soc_projection.soc_percent
            if soc_pct < self.CRITICAL_SOC_THRESHOLD_PCT
        )

        # SoC risk increases with critical hours
        # 4+ critical hours = max risk
        soc_risk = min(1.0, critical_soc_hours / 4 + low_soc_hours / 12)

        # Calculate demand risk (supply shortfalls)
        deficits = []
        deficit_hours = []
        for h in range(min(len(pv_forecast), len(demand_forecast))):
            # Available supply = PV + battery discharge capacity
            available_supply = pv_forecast[h] + self.battery_power_kw
            if demand_forecast[h] > available_supply:
                deficit = demand_forecast[h] - available_supply
                deficits.append(deficit)
                deficit_hours.append(h)

        peak_deficit = max(deficits) if deficits else 0
        # Demand risk based on number of deficit hours
        demand_risk = min(1.0, len(deficits) / 6)  # 6+ deficit hours = max risk

        # Weather risk
        # Severe weather can damage equipment or reduce PV output
        weather_risk = 0.0
        if weather_severe:
            weather_risk = 0.5
        if precipitation_mm > 50:  # Heavy rain
            weather_risk = max(weather_risk, 0.4)
        elif precipitation_mm > 20:  # Moderate rain
            weather_risk = max(weather_risk, 0.2)

        # Overall risk (weighted combination)
        overall_risk = (
            soc_risk * 0.4 +      # SoC is most critical
            demand_risk * 0.4 +   # Demand balance also critical
            weather_risk * 0.2    # Weather is secondary
        )

        # Determine alert level
        if overall_risk >= self.CRITICAL_RISK or critical_soc_hours >= 2:
            alert_level = "critical"
        elif overall_risk >= self.WARNING_RISK or low_soc_hours >= 4:
            alert_level = "warning"
        elif overall_risk >= self.WATCH_RISK or low_soc_hours >= 2:
            alert_level = "watch"
        else:
            alert_level = "normal"

        # Generate recommendations
        recommendations = self._generate_recommendations(
            soc_risk=soc_risk,
            demand_risk=demand_risk,
            weather_risk=weather_risk,
            low_soc_hours=low_soc_hours,
            deficit_hours=deficit_hours,
            peak_deficit=peak_deficit,
        )

        return RiskAssessment(
            site_id=self.site_id,
            assessment_time=datetime.utcnow(),
            overall_risk=round(overall_risk, 3),
            soc_risk=round(soc_risk, 3),
            demand_risk=round(demand_risk, 3),
            weather_risk=round(weather_risk, 3),
            peak_deficit_kw=round(peak_deficit, 2),
            low_soc_hours=low_soc_hours,
            critical_soc_hours=critical_soc_hours,
            alert_level=alert_level,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        soc_risk: float,
        demand_risk: float,
        weather_risk: float,
        low_soc_hours: int,
        deficit_hours: List[int],
        peak_deficit: float,
    ) -> List[str]:
        """Generate actionable recommendations based on risks."""
        recommendations = []

        # SoC recommendations
        if soc_risk > 0.5:
            recommendations.append(
                "Battery critically low - consider load shedding for non-essential circuits"
            )
        elif soc_risk > 0.3:
            recommendations.append(
                "Battery below target - reduce non-essential loads during evening peak (18:00-21:00)"
            )

        # Demand recommendations
        if demand_risk > 0.3 and deficit_hours:
            hours_str = ", ".join(f"{h}:00" for h in deficit_hours[:5])
            recommendations.append(
                f"Supply deficit expected at {hours_str} - increase prices or activate demand response"
            )

        if peak_deficit > 10:
            recommendations.append(
                f"Peak deficit of {peak_deficit:.1f} kW expected - may need to curtail {peak_deficit:.0f} kW of load"
            )

        # Weather recommendations
        if weather_risk > 0.3:
            recommendations.append(
                "Severe weather expected - prepare backup protocols and monitor equipment"
            )

        # General low SoC warning
        if low_soc_hours > 0:
            recommendations.append(
                f"Battery expected below 25% for {low_soc_hours} hours - "
                "send notifications to customers for load shifting"
            )

        # Solar surplus opportunity
        if soc_risk < 0.2 and demand_risk < 0.2:
            recommendations.append(
                "Low risk period - good time for maintenance or testing"
            )

        return recommendations

    def get_alert_color(self, alert_level: str) -> str:
        """Get color code for alert level (for UI display)."""
        colors = {
            "normal": "#22c55e",   # Green
            "watch": "#eab308",    # Yellow
            "warning": "#f97316",  # Orange
            "critical": "#ef4444", # Red
        }
        return colors.get(alert_level, "#6b7280")  # Gray default

    def should_send_notification(self, risk: RiskAssessment) -> bool:
        """Determine if operator should be notified."""
        return risk.alert_level in ("warning", "critical")
