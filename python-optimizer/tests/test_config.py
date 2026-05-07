"""
Tests for KORA configuration system.
"""

import pytest
import tempfile
from pathlib import Path

from kora.config import (
    SiteConfig,
    BatteryConfig,
    SolarConfig,
    PricingConfig,
    DemandConfig,
    ConfigValidationError,
)


class TestBatteryConfig:
    """Test battery configuration validation."""

    def test_valid_config(self):
        config = BatteryConfig(
            capacity_kwh=100,
            power_kw=50,
            soc_min_percent=20,
            soc_max_percent=95,
        )
        errors = config.validate()
        assert errors == []

    def test_invalid_capacity(self):
        config = BatteryConfig(capacity_kwh=-100, power_kw=50)
        errors = config.validate()
        assert any("capacity_kwh" in e for e in errors)

    def test_invalid_soc_range(self):
        config = BatteryConfig(
            capacity_kwh=100,
            power_kw=50,
            soc_min_percent=80,
            soc_max_percent=70,  # min > max
        )
        errors = config.validate()
        assert any("soc" in e.lower() for e in errors)

    def test_soc_kwh_properties(self):
        config = BatteryConfig(
            capacity_kwh=100,
            power_kw=50,
            soc_min_percent=20,
            soc_max_percent=95,
        )
        assert config.soc_min_kwh == 20.0
        assert config.soc_max_kwh == 95.0


class TestPricingConfig:
    """Test pricing configuration validation."""

    def test_valid_config(self):
        config = PricingConfig(
            min_price=0.10,
            max_price=0.30,
            reference_price=0.20,
        )
        errors = config.validate()
        assert errors == []

    def test_invalid_price_range(self):
        config = PricingConfig(
            min_price=0.30,
            max_price=0.10,  # max < min
            reference_price=0.20,
        )
        errors = config.validate()
        assert any("max_price" in e for e in errors)

    def test_reference_out_of_bounds(self):
        config = PricingConfig(
            min_price=0.10,
            max_price=0.30,
            reference_price=0.50,  # outside bounds
        )
        errors = config.validate()
        assert any("reference_price" in e for e in errors)


class TestSiteConfig:
    """Test full site configuration."""

    def test_from_dict(self):
        data = {
            "site_id": "test-site",
            "site_name": "Test Site",
            "battery": {
                "capacity_kwh": 100,
                "power_kw": 50,
            },
            "solar": {
                "capacity_kw": 100,
            },
            "pricing": {
                "min_price": 0.10,
                "max_price": 0.30,
                "reference_price": 0.20,
            },
        }

        config = SiteConfig.from_dict(data)

        assert config.site_id == "test-site"
        assert config.site_name == "Test Site"
        assert config.battery.capacity_kwh == 100
        assert config.solar.capacity_kw == 100
        assert config.pricing.min_price == 0.10

    def test_from_yaml(self):
        yaml_content = """
site_id: yaml-test
site_name: YAML Test Site
battery:
  capacity_kwh: 115
  power_kw: 54
solar:
  capacity_kw: 118.5
pricing:
  min_price: 1000
  max_price: 2500
  reference_price: 1750
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            config = SiteConfig.from_yaml(f.name)

            assert config.site_id == "yaml-test"
            assert config.battery.capacity_kwh == 115
            assert config.pricing.reference_price == 1750

    def test_to_dict_roundtrip(self):
        original = SiteConfig(
            site_id="roundtrip",
            site_name="Roundtrip Test",
            battery=BatteryConfig(capacity_kwh=100, power_kw=50),
            solar=SolarConfig(capacity_kw=100),
            pricing=PricingConfig(min_price=0.10, max_price=0.30, reference_price=0.20),
        )

        data = original.to_dict()
        restored = SiteConfig.from_dict(data)

        assert restored.site_id == original.site_id
        assert restored.battery.capacity_kwh == original.battery.capacity_kwh
        assert restored.pricing.reference_price == original.pricing.reference_price

    def test_validation_errors(self):
        data = {
            "site_id": "",  # Invalid: empty
            "site_name": "Test",
            "battery": {
                "capacity_kwh": -100,  # Invalid: negative
                "power_kw": 50,
            },
        }

        with pytest.raises(ConfigValidationError) as exc_info:
            SiteConfig.from_dict(data)
            errors = SiteConfig.from_dict(data).validate()

        # Should have validation errors
        config = SiteConfig.from_dict(data)
        errors = config.validate()
        assert len(errors) > 0

    def test_missing_file(self):
        with pytest.raises(ConfigValidationError):
            SiteConfig.from_yaml("/nonexistent/path/config.yaml")
