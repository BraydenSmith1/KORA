"""
KORA Site Configuration System

Provides YAML-based configuration for microgrid sites with validation.
Each site has its own config file defining physical specs, pricing bounds,
and operational parameters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


@dataclass
class BatteryConfig:
    """Battery storage configuration."""
    capacity_kwh: float
    power_kw: float
    soc_min_percent: float = 20.0
    soc_max_percent: float = 95.0
    efficiency_charge: float = 0.94
    efficiency_discharge: float = 0.94
    cycle_cost_per_kwh: float = 0.01

    def validate(self) -> List[str]:
        errors = []
        if self.capacity_kwh <= 0:
            errors.append("battery.capacity_kwh must be positive")
        if self.power_kw <= 0:
            errors.append("battery.power_kw must be positive")
        if not (0 <= self.soc_min_percent < self.soc_max_percent <= 100):
            errors.append("battery.soc_min_percent must be < soc_max_percent, both in [0, 100]")
        if not (0 < self.efficiency_charge <= 1):
            errors.append("battery.efficiency_charge must be in (0, 1]")
        if not (0 < self.efficiency_discharge <= 1):
            errors.append("battery.efficiency_discharge must be in (0, 1]")
        return errors

    @property
    def soc_min_kwh(self) -> float:
        return self.capacity_kwh * self.soc_min_percent / 100

    @property
    def soc_max_kwh(self) -> float:
        return self.capacity_kwh * self.soc_max_percent / 100


@dataclass
class SolarConfig:
    """Solar array configuration."""
    capacity_kw: float
    daily_production_kwh: Optional[float] = None  # For reference/validation

    def validate(self) -> List[str]:
        errors = []
        if self.capacity_kw <= 0:
            errors.append("solar.capacity_kw must be positive")
        return errors


@dataclass
class PricingConfig:
    """Dynamic pricing bounds and parameters."""
    min_price: float  # Minimum allowed price (affordability floor)
    max_price: float  # Maximum allowed price (regulatory cap)
    reference_price: float  # Baseline price customers expect
    currency: str = "USD"
    currency_symbol: str = "$"

    def validate(self) -> List[str]:
        errors = []
        if self.min_price < 0:
            errors.append("pricing.min_price cannot be negative")
        if self.max_price <= self.min_price:
            errors.append("pricing.max_price must be > min_price")
        if not (self.min_price <= self.reference_price <= self.max_price):
            errors.append("pricing.reference_price must be between min_price and max_price")
        return errors


@dataclass
class DemandConfig:
    """Demand response parameters."""
    elasticity: float = 0.6  # Price elasticity of demand
    peak_load_kw: float = 50.0
    base_load_kw: float = 8.0

    def validate(self) -> List[str]:
        errors = []
        if not (0 <= self.elasticity <= 2):
            errors.append("demand.elasticity should be in [0, 2]")
        if self.peak_load_kw <= 0:
            errors.append("demand.peak_load_kw must be positive")
        if self.base_load_kw < 0:
            errors.append("demand.base_load_kw cannot be negative")
        return errors


@dataclass
class GridConfig:
    """Grid connection parameters (for grid-tied systems)."""
    connected: bool = False
    import_limit_kw: Optional[float] = None
    export_limit_kw: Optional[float] = None
    wholesale_price: Optional[float] = None

    def validate(self) -> List[str]:
        errors = []
        if self.connected:
            if self.import_limit_kw is not None and self.import_limit_kw < 0:
                errors.append("grid.import_limit_kw cannot be negative")
            if self.export_limit_kw is not None and self.export_limit_kw < 0:
                errors.append("grid.export_limit_kw cannot be negative")
        return errors


@dataclass
class OptimizerConfig:
    """Optimizer runtime parameters."""
    horizon_hours: int = 24
    timestep_hours: float = 1.0
    solver: str = "highs"
    time_limit_sec: int = 60
    curtailment_penalty: float = 1500.0  # Value per kWh of curtailed energy
    blackout_penalty: float = 5000.0  # Penalty per kWh of unmet demand

    def validate(self) -> List[str]:
        errors = []
        if self.horizon_hours < 1:
            errors.append("optimizer.horizon_hours must be >= 1")
        if self.timestep_hours <= 0:
            errors.append("optimizer.timestep_hours must be positive")
        if self.time_limit_sec < 1:
            errors.append("optimizer.time_limit_sec must be >= 1")
        return errors


@dataclass
class TelemetryConfig:
    """Telemetry and data collection configuration."""
    modbus_host: Optional[str] = None
    modbus_port: int = 502
    poll_interval_sec: float = 1.0
    api_url: Optional[str] = None
    api_key: Optional[str] = None

    def validate(self) -> List[str]:
        return []  # All fields are optional


@dataclass
class AlertsConfig:
    """Alerting configuration."""
    webhook_url: Optional[str] = None
    email: Optional[str] = None
    sms_number: Optional[str] = None
    alert_on_solver_failure: bool = True
    alert_on_high_curtailment: bool = True
    curtailment_threshold_percent: float = 20.0

    def validate(self) -> List[str]:
        errors = []
        if not (0 <= self.curtailment_threshold_percent <= 100):
            errors.append("alerts.curtailment_threshold_percent must be in [0, 100]")
        return errors


@dataclass
class SiteConfig:
    """
    Complete site configuration.

    This is the main configuration object loaded from YAML files.
    """
    site_id: str
    site_name: str
    location: Optional[str] = None
    timezone: str = "UTC"

    battery: BatteryConfig = field(default_factory=lambda: BatteryConfig(
        capacity_kwh=100, power_kw=50
    ))
    solar: SolarConfig = field(default_factory=lambda: SolarConfig(capacity_kw=100))
    pricing: PricingConfig = field(default_factory=lambda: PricingConfig(
        min_price=0.10, max_price=0.30, reference_price=0.20
    ))
    demand: DemandConfig = field(default_factory=DemandConfig)
    grid: GridConfig = field(default_factory=GridConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    alerts: AlertsConfig = field(default_factory=AlertsConfig)

    def validate(self) -> List[str]:
        """Validate all configuration sections."""
        errors = []

        if not self.site_id:
            errors.append("site_id is required")
        if not self.site_name:
            errors.append("site_name is required")

        errors.extend(self.battery.validate())
        errors.extend(self.solar.validate())
        errors.extend(self.pricing.validate())
        errors.extend(self.demand.validate())
        errors.extend(self.grid.validate())
        errors.extend(self.optimizer.validate())
        errors.extend(self.telemetry.validate())
        errors.extend(self.alerts.validate())

        return errors

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SiteConfig":
        """Create SiteConfig from a dictionary (e.g., parsed YAML)."""

        battery_data = data.get("battery", {})
        battery = BatteryConfig(
            capacity_kwh=battery_data.get("capacity_kwh", 100),
            power_kw=battery_data.get("power_kw", 50),
            soc_min_percent=battery_data.get("soc_min_percent", 20),
            soc_max_percent=battery_data.get("soc_max_percent", 95),
            efficiency_charge=battery_data.get("efficiency_charge", 0.94),
            efficiency_discharge=battery_data.get("efficiency_discharge", 0.94),
            cycle_cost_per_kwh=battery_data.get("cycle_cost_per_kwh", 0.01),
        )

        solar_data = data.get("solar", {})
        solar = SolarConfig(
            capacity_kw=solar_data.get("capacity_kw", 100),
            daily_production_kwh=solar_data.get("daily_production_kwh"),
        )

        pricing_data = data.get("pricing", {})
        pricing = PricingConfig(
            min_price=pricing_data.get("min_price", 0.10),
            max_price=pricing_data.get("max_price", 0.30),
            reference_price=pricing_data.get("reference_price", 0.20),
            currency=pricing_data.get("currency", "USD"),
            currency_symbol=pricing_data.get("currency_symbol", "$"),
        )

        demand_data = data.get("demand", {})
        demand = DemandConfig(
            elasticity=demand_data.get("elasticity", 0.6),
            peak_load_kw=demand_data.get("peak_load_kw", 50),
            base_load_kw=demand_data.get("base_load_kw", 8),
        )

        grid_data = data.get("grid", {})
        grid = GridConfig(
            connected=grid_data.get("connected", False),
            import_limit_kw=grid_data.get("import_limit_kw"),
            export_limit_kw=grid_data.get("export_limit_kw"),
            wholesale_price=grid_data.get("wholesale_price"),
        )

        optimizer_data = data.get("optimizer", {})
        optimizer = OptimizerConfig(
            horizon_hours=optimizer_data.get("horizon_hours", 24),
            timestep_hours=optimizer_data.get("timestep_hours", 1.0),
            solver=optimizer_data.get("solver", "highs"),
            time_limit_sec=optimizer_data.get("time_limit_sec", 60),
            curtailment_penalty=optimizer_data.get("curtailment_penalty", 1500),
            blackout_penalty=optimizer_data.get("blackout_penalty", 5000),
        )

        telemetry_data = data.get("telemetry", {})
        telemetry = TelemetryConfig(
            modbus_host=telemetry_data.get("modbus_host"),
            modbus_port=telemetry_data.get("modbus_port", 502),
            poll_interval_sec=telemetry_data.get("poll_interval_sec", 1.0),
            api_url=telemetry_data.get("api_url"),
            api_key=telemetry_data.get("api_key"),
        )

        alerts_data = data.get("alerts", {})
        alerts = AlertsConfig(
            webhook_url=alerts_data.get("webhook_url"),
            email=alerts_data.get("email"),
            sms_number=alerts_data.get("sms_number"),
            alert_on_solver_failure=alerts_data.get("alert_on_solver_failure", True),
            alert_on_high_curtailment=alerts_data.get("alert_on_high_curtailment", True),
            curtailment_threshold_percent=alerts_data.get("curtailment_threshold_percent", 20),
        )

        return cls(
            site_id=data.get("site_id", "unknown"),
            site_name=data.get("site_name", "Unknown Site"),
            location=data.get("location"),
            timezone=data.get("timezone", "UTC"),
            battery=battery,
            solar=solar,
            pricing=pricing,
            demand=demand,
            grid=grid,
            optimizer=optimizer,
            telemetry=telemetry,
            alerts=alerts,
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SiteConfig":
        """Load configuration from a YAML file."""
        path = Path(path)
        if not path.exists():
            raise ConfigValidationError(f"Config file not found: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ConfigValidationError(f"Config file must contain a YAML mapping: {path}")

        config = cls.from_dict(data)

        errors = config.validate()
        if errors:
            raise ConfigValidationError(
                f"Configuration validation failed for {path}:\n" +
                "\n".join(f"  - {e}" for e in errors)
            )

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (for serialization)."""
        return {
            "site_id": self.site_id,
            "site_name": self.site_name,
            "location": self.location,
            "timezone": self.timezone,
            "battery": {
                "capacity_kwh": self.battery.capacity_kwh,
                "power_kw": self.battery.power_kw,
                "soc_min_percent": self.battery.soc_min_percent,
                "soc_max_percent": self.battery.soc_max_percent,
                "efficiency_charge": self.battery.efficiency_charge,
                "efficiency_discharge": self.battery.efficiency_discharge,
                "cycle_cost_per_kwh": self.battery.cycle_cost_per_kwh,
            },
            "solar": {
                "capacity_kw": self.solar.capacity_kw,
                "daily_production_kwh": self.solar.daily_production_kwh,
            },
            "pricing": {
                "min_price": self.pricing.min_price,
                "max_price": self.pricing.max_price,
                "reference_price": self.pricing.reference_price,
                "currency": self.pricing.currency,
                "currency_symbol": self.pricing.currency_symbol,
            },
            "demand": {
                "elasticity": self.demand.elasticity,
                "peak_load_kw": self.demand.peak_load_kw,
                "base_load_kw": self.demand.base_load_kw,
            },
            "grid": {
                "connected": self.grid.connected,
                "import_limit_kw": self.grid.import_limit_kw,
                "export_limit_kw": self.grid.export_limit_kw,
                "wholesale_price": self.grid.wholesale_price,
            },
            "optimizer": {
                "horizon_hours": self.optimizer.horizon_hours,
                "timestep_hours": self.optimizer.timestep_hours,
                "solver": self.optimizer.solver,
                "time_limit_sec": self.optimizer.time_limit_sec,
                "curtailment_penalty": self.optimizer.curtailment_penalty,
                "blackout_penalty": self.optimizer.blackout_penalty,
            },
            "telemetry": {
                "modbus_host": self.telemetry.modbus_host,
                "modbus_port": self.telemetry.modbus_port,
                "poll_interval_sec": self.telemetry.poll_interval_sec,
                "api_url": self.telemetry.api_url,
                "api_key": self.telemetry.api_key,
            },
            "alerts": {
                "webhook_url": self.alerts.webhook_url,
                "email": self.alerts.email,
                "sms_number": self.alerts.sms_number,
                "alert_on_solver_failure": self.alerts.alert_on_solver_failure,
                "alert_on_high_curtailment": self.alerts.alert_on_high_curtailment,
                "curtailment_threshold_percent": self.alerts.curtailment_threshold_percent,
            },
        }

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to a YAML file."""
        path = Path(path)
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)


def load_config(path: str | Path | None = None) -> SiteConfig:
    """
    Load site configuration from a YAML file.

    If no path is provided, looks for:
    1. KORA_CONFIG environment variable
    2. ./config.yaml
    3. ./sites/default.yaml
    """
    if path is not None:
        return SiteConfig.from_yaml(path)

    # Check environment variable
    env_path = os.environ.get("KORA_CONFIG")
    if env_path and Path(env_path).exists():
        return SiteConfig.from_yaml(env_path)

    # Check common locations
    for candidate in ["config.yaml", "sites/default.yaml", "kora.yaml"]:
        if Path(candidate).exists():
            return SiteConfig.from_yaml(candidate)

    raise ConfigValidationError(
        "No configuration file found. Create a config.yaml or set KORA_CONFIG environment variable."
    )
