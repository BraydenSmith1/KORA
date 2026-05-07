"""
KORA Site Configuration Loader

Loads and validates YAML configuration files for site parameters.
Provides type-safe access to configuration values.
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


@dataclass
class SolarConfig:
    capacity_kwp: float
    panel_count: int
    panel_model: str
    daily_avg_production_kwh: float
    sunrise_hour: int = 6
    sunset_hour: int = 18


@dataclass
class BatteryConfig:
    capacity_kwh: float
    power_kw: float
    module_count: int
    module_model: str
    charge_efficiency: float
    discharge_efficiency: float
    soc_min_percent: float
    soc_max_percent: float


@dataclass
class InverterConfig:
    capacity_kw: float
    count: int
    model: str


@dataclass
class CustomersConfig:
    total_connections: int
    breakdown: Dict[str, int]
    peak_load_kw: float


@dataclass
class TimeOfUseConfig:
    peak_start_hour: int
    peak_end_hour: int
    intermediate_start_hour: int
    intermediate_end_hour: int


@dataclass
class PricingConfig:
    currency: str
    currency_symbol: str
    time_of_use: TimeOfUseConfig
    customer_rates: Dict[str, Dict[str, float]]
    fixed_fees: Dict[str, float]


@dataclass
class OptimizationConfig:
    price_elasticity: float
    min_discount_percent: float
    max_discount_percent: float
    price_stability_minutes: int
    targets: Dict[str, float]


@dataclass
class ModbusConfig:
    host: str
    port: int
    slave_id: int
    poll_interval_sec: int
    retry_count: int
    retry_delay_sec: int


@dataclass
class ApiConfig:
    base_url: str
    telemetry_push_interval_sec: int
    token: Optional[str] = None


@dataclass
class LoggingConfig:
    level: str
    format: str
    file: Optional[str] = None


@dataclass
class AlertsConfig:
    enabled: bool
    thresholds: Dict[str, float]


@dataclass
class SiteInfo:
    id: str
    name: str
    location: str
    timezone: str
    coordinates: Dict[str, float]


@dataclass
class SiteConfig:
    """Complete site configuration"""
    site: SiteInfo
    solar: SolarConfig
    battery: BatteryConfig
    inverter: InverterConfig
    customers: CustomersConfig
    pricing: PricingConfig
    optimization: OptimizationConfig
    modbus: ModbusConfig
    api: ApiConfig
    logging: LoggingConfig
    alerts: AlertsConfig


def load_config(config_path: str = None) -> SiteConfig:
    """
    Load and validate site configuration from YAML file.

    Args:
        config_path: Path to YAML config file. If None, looks for:
                     1. KORA_CONFIG environment variable
                     2. ./config/site_config.yaml
                     3. ./site_config.yaml

    Returns:
        Validated SiteConfig object

    Raises:
        ConfigValidationError: If config is invalid or missing required fields
        FileNotFoundError: If config file not found
    """
    # Find config file
    if config_path is None:
        config_path = os.environ.get('KORA_CONFIG')

    if config_path is None:
        # Search in common locations
        search_paths = [
            Path(__file__).parent / 'site_config.yaml',
            Path.cwd() / 'config' / 'site_config.yaml',
            Path.cwd() / 'site_config.yaml',
        ]
        for path in search_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path is None or not Path(config_path).exists():
        raise FileNotFoundError(
            f"Config file not found. Set KORA_CONFIG environment variable or "
            f"create config/site_config.yaml"
        )

    # Load YAML
    with open(config_path, 'r') as f:
        raw_config = yaml.safe_load(f)

    # Validate and parse
    try:
        config = _parse_config(raw_config)
        _validate_config(config)
        print(f"✓ Config loaded from {config_path}")
        return config
    except Exception as e:
        raise ConfigValidationError(f"Config validation failed: {e}")


def _parse_config(raw: Dict[str, Any]) -> SiteConfig:
    """Parse raw YAML dict into typed config objects"""

    # Site info
    site_raw = raw.get('site', {})
    site = SiteInfo(
        id=site_raw.get('id', 'unknown'),
        name=site_raw.get('name', 'Unknown Site'),
        location=site_raw.get('location', ''),
        timezone=site_raw.get('timezone', 'UTC'),
        coordinates=site_raw.get('coordinates', {'latitude': 0, 'longitude': 0})
    )

    # Solar
    solar_raw = raw.get('solar', {})
    solar = SolarConfig(
        capacity_kwp=solar_raw.get('capacity_kwp', 0),
        panel_count=solar_raw.get('panel_count', 0),
        panel_model=solar_raw.get('panel_model', ''),
        daily_avg_production_kwh=solar_raw.get('daily_avg_production_kwh', 0),
        sunrise_hour=solar_raw.get('sunrise_hour', 6),
        sunset_hour=solar_raw.get('sunset_hour', 18)
    )

    # Battery
    battery_raw = raw.get('battery', {})
    battery = BatteryConfig(
        capacity_kwh=battery_raw.get('capacity_kwh', 0),
        power_kw=battery_raw.get('power_kw', 0),
        module_count=battery_raw.get('module_count', 0),
        module_model=battery_raw.get('module_model', ''),
        charge_efficiency=battery_raw.get('charge_efficiency', 0.9),
        discharge_efficiency=battery_raw.get('discharge_efficiency', 0.9),
        soc_min_percent=battery_raw.get('soc_min_percent', 20),
        soc_max_percent=battery_raw.get('soc_max_percent', 95)
    )

    # Inverter
    inverter_raw = raw.get('inverter', {})
    inverter = InverterConfig(
        capacity_kw=inverter_raw.get('capacity_kw', 0),
        count=inverter_raw.get('count', 1),
        model=inverter_raw.get('model', '')
    )

    # Customers
    customers_raw = raw.get('customers', {})
    customers = CustomersConfig(
        total_connections=customers_raw.get('total_connections', 0),
        breakdown=customers_raw.get('breakdown', {}),
        peak_load_kw=customers_raw.get('peak_load_kw', 0)
    )

    # Pricing
    pricing_raw = raw.get('pricing', {})
    tou_raw = pricing_raw.get('time_of_use', {})
    time_of_use = TimeOfUseConfig(
        peak_start_hour=tou_raw.get('peak', {}).get('start_hour', 17),
        peak_end_hour=tou_raw.get('peak', {}).get('end_hour', 23),
        intermediate_start_hour=tou_raw.get('intermediate', {}).get('start_hour', 8),
        intermediate_end_hour=tou_raw.get('intermediate', {}).get('end_hour', 17)
    )
    pricing = PricingConfig(
        currency=pricing_raw.get('currency', 'USD'),
        currency_symbol=pricing_raw.get('currency_symbol', '$'),
        time_of_use=time_of_use,
        customer_rates=pricing_raw.get('customer_rates', {}),
        fixed_fees=pricing_raw.get('fixed_fees', {})
    )

    # Optimization
    opt_raw = raw.get('optimization', {})
    optimization = OptimizationConfig(
        price_elasticity=opt_raw.get('price_elasticity', 0.5),
        min_discount_percent=opt_raw.get('min_discount_percent', 0),
        max_discount_percent=opt_raw.get('max_discount_percent', 30),
        price_stability_minutes=opt_raw.get('price_stability_minutes', 30),
        targets=opt_raw.get('targets', {})
    )

    # Modbus
    modbus_raw = raw.get('modbus', {})
    modbus = ModbusConfig(
        host=modbus_raw.get('host', '127.0.0.1'),
        port=modbus_raw.get('port', 502),
        slave_id=modbus_raw.get('slave_id', 1),
        poll_interval_sec=modbus_raw.get('poll_interval_sec', 10),
        retry_count=modbus_raw.get('retry_count', 3),
        retry_delay_sec=modbus_raw.get('retry_delay_sec', 5)
    )

    # API
    api_raw = raw.get('api', {})
    api = ApiConfig(
        base_url=api_raw.get('base_url', 'http://localhost:4000'),
        telemetry_push_interval_sec=api_raw.get('telemetry_push_interval_sec', 10),
        token=os.environ.get('KORA_API_TOKEN', api_raw.get('token'))
    )

    # Logging
    log_raw = raw.get('logging', {})
    logging_config = LoggingConfig(
        level=log_raw.get('level', 'INFO'),
        format=log_raw.get('format', 'json'),
        file=log_raw.get('file')
    )

    # Alerts
    alerts_raw = raw.get('alerts', {})
    alerts = AlertsConfig(
        enabled=alerts_raw.get('enabled', True),
        thresholds=alerts_raw.get('thresholds', {})
    )

    return SiteConfig(
        site=site,
        solar=solar,
        battery=battery,
        inverter=inverter,
        customers=customers,
        pricing=pricing,
        optimization=optimization,
        modbus=modbus,
        api=api,
        logging=logging_config,
        alerts=alerts
    )


def _validate_config(config: SiteConfig) -> None:
    """Validate configuration values"""
    errors = []

    # Required positive values
    if config.solar.capacity_kwp <= 0:
        errors.append("solar.capacity_kwp must be positive")

    if config.battery.capacity_kwh <= 0:
        errors.append("battery.capacity_kwh must be positive")

    if config.battery.power_kw <= 0:
        errors.append("battery.power_kw must be positive")

    # Efficiency bounds
    if not (0 < config.battery.charge_efficiency <= 1):
        errors.append("battery.charge_efficiency must be between 0 and 1")

    if not (0 < config.battery.discharge_efficiency <= 1):
        errors.append("battery.discharge_efficiency must be between 0 and 1")

    # SOC bounds
    if config.battery.soc_min_percent < 0 or config.battery.soc_min_percent > 100:
        errors.append("battery.soc_min_percent must be 0-100")

    if config.battery.soc_max_percent <= config.battery.soc_min_percent:
        errors.append("battery.soc_max_percent must be greater than soc_min_percent")

    # Hour ranges
    if not (0 <= config.solar.sunrise_hour < 24):
        errors.append("solar.sunrise_hour must be 0-23")

    if not (0 <= config.solar.sunset_hour < 24):
        errors.append("solar.sunset_hour must be 0-23")

    # Price elasticity
    if not (0 <= config.optimization.price_elasticity <= 2):
        errors.append("optimization.price_elasticity should be 0-2 (typical 0.3-0.8)")

    # Logging level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    if config.logging.level.upper() not in valid_levels:
        errors.append(f"logging.level must be one of: {valid_levels}")

    if errors:
        raise ConfigValidationError("\n".join(errors))


def print_config_summary(config: SiteConfig) -> None:
    """Print a human-readable config summary"""
    print("\n" + "=" * 50)
    print(f"KORA Site Configuration: {config.site.name}")
    print("=" * 50)
    print(f"\nSite ID: {config.site.id}")
    print(f"Location: {config.site.location}")
    print(f"Timezone: {config.site.timezone}")
    print(f"\nSolar: {config.solar.capacity_kwp} kWp ({config.solar.panel_count} panels)")
    print(f"Battery: {config.battery.capacity_kwh} kWh / {config.battery.power_kw} kW")
    print(f"Inverter: {config.inverter.capacity_kw} kW ({config.inverter.count}x)")
    print(f"Customers: {config.customers.total_connections} connections")
    print(f"Peak Load: {config.customers.peak_load_kw} kW")
    print(f"\nOptimization:")
    print(f"  Price Elasticity: {config.optimization.price_elasticity}")
    print(f"  Max Discount: {config.optimization.max_discount_percent}%")
    print(f"\nModbus: {config.modbus.host}:{config.modbus.port}")
    print(f"API: {config.api.base_url}")
    print(f"Logging: {config.logging.level} ({config.logging.format})")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    # Test config loading
    try:
        config = load_config()
        print_config_summary(config)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
