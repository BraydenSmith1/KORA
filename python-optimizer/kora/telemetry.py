"""
KORA Telemetry Collection

Production-ready telemetry collection with:
- Modbus TCP polling with retry logic
- Circuit breaker for connection failures
- Data validation and sanitization
- API posting with buffering
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests

from .config import SiteConfig, TelemetryConfig
from .errors import (
    CircuitBreaker,
    ModbusError,
    ApiError,
    RetryConfig,
    RetryStrategy,
    sanitize_telemetry,
    with_circuit_breaker,
)
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class ModbusRegister:
    """Modbus register definition."""
    name: str
    address: int
    unit: int = 1
    scale: float = 1.0
    kind: str = "holding"  # "holding" or "input"


@dataclass
class TelemetryFrame:
    """A single telemetry reading."""
    timestamp: float
    signals: Dict[str, float]
    quality: str = "good"
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "signals": self.signals,
            "quality": self.quality,
            "errors": self.errors if self.errors else None,
        }


class ModbusCollector:
    """
    Modbus TCP collector with production features.

    Features:
    - Automatic reconnection
    - Circuit breaker pattern
    - Data validation
    - Buffered API posting
    """

    def __init__(
        self,
        host: str,
        port: int = 502,
        registers: Optional[List[ModbusRegister]] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.host = host
        self.port = port
        self.registers = registers or []
        self.retry_config = retry_config or RetryConfig(
            max_attempts=3,
            initial_delay_sec=1.0,
            strategy=RetryStrategy.EXPONENTIAL_JITTER,
        )

        # Circuit breaker for Modbus connection
        self.circuit = CircuitBreaker(
            name=f"modbus_{host}",
            failure_threshold=5,
            success_threshold=2,
            timeout_sec=30.0,
        )

        self._client = None
        self._connected = False
        self._last_read_time = 0
        self._consecutive_failures = 0

    @classmethod
    def from_config(cls, config: TelemetryConfig) -> "ModbusCollector":
        """Create collector from TelemetryConfig."""
        return cls(
            host=config.modbus_host or "127.0.0.1",
            port=config.modbus_port,
        )

    @classmethod
    def from_json_config(cls, path: str | Path) -> "ModbusCollector":
        """Load collector configuration from JSON file."""
        with open(path, "r") as f:
            raw = json.load(f)

        registers = [
            ModbusRegister(
                name=r["name"],
                address=r["address"],
                unit=r.get("unit", 1),
                scale=r.get("scale", 1.0),
                kind=r.get("kind", "holding"),
            )
            for r in raw.get("registers", [])
        ]

        return cls(
            host=raw.get("host", "127.0.0.1"),
            port=raw.get("port", 502),
            registers=registers,
        )

    async def connect(self) -> bool:
        """Establish Modbus connection."""
        try:
            from pymodbus.client import AsyncModbusTcpClient

            self._client = AsyncModbusTcpClient(self.host, port=self.port)
            connected = await self._client.connect()

            if connected:
                self._connected = True
                self._consecutive_failures = 0
                logger.info(f"Connected to Modbus at {self.host}:{self.port}")
            else:
                logger.warning(f"Failed to connect to Modbus at {self.host}:{self.port}")

            return connected

        except Exception as e:
            logger.error(f"Modbus connection error: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close Modbus connection."""
        if self._client:
            self._client.close()
            self._connected = False
            logger.info("Disconnected from Modbus")

    async def _read_register(self, reg: ModbusRegister) -> Optional[float]:
        """Read a single register with error handling."""
        try:
            from pymodbus.exceptions import ModbusException

            if not self._client or not self._connected:
                return None

            if reg.kind == "holding":
                result = await self._client.read_holding_registers(
                    reg.address, 1, slave=reg.unit
                )
            else:
                result = await self._client.read_input_registers(
                    reg.address, 1, slave=reg.unit
                )

            if result.isError():
                logger.warning(f"Modbus error reading {reg.name}: {result}")
                return None

            value = result.registers[0] * reg.scale
            return value

        except Exception as e:
            logger.warning(f"Error reading register {reg.name}: {e}")
            return None

    async def read_all(self) -> TelemetryFrame:
        """Read all configured registers."""
        timestamp = time.time()
        signals = {}
        errors = []

        # Check circuit breaker
        if not self.circuit.can_execute():
            return TelemetryFrame(
                timestamp=timestamp,
                signals={},
                quality="circuit_open",
                errors=["Circuit breaker is open"],
            )

        # Ensure connected
        if not self._connected:
            connected = await self.connect()
            if not connected:
                self.circuit.record_failure(ModbusError("Connection failed"))
                return TelemetryFrame(
                    timestamp=timestamp,
                    signals={},
                    quality="disconnected",
                    errors=["Failed to connect to Modbus"],
                )

        # Read each register
        for reg in self.registers:
            value = await self._read_register(reg)
            if value is not None:
                signals[reg.name] = value
            else:
                errors.append(f"Failed to read {reg.name}")

        # Determine quality
        if not errors:
            quality = "good"
            self.circuit.record_success()
            self._consecutive_failures = 0
        elif len(errors) < len(self.registers):
            quality = "partial"
            self._consecutive_failures += 1
        else:
            quality = "bad"
            self._consecutive_failures += 1
            self.circuit.record_failure(ModbusError("All reads failed"))

        # Reconnect if too many failures
        if self._consecutive_failures >= 3:
            logger.warning("Too many consecutive failures, reconnecting...")
            await self.disconnect()
            await self.connect()

        self._last_read_time = timestamp

        return TelemetryFrame(
            timestamp=timestamp,
            signals=sanitize_telemetry(signals),
            quality=quality,
            errors=errors,
        )


class ApiPoster:
    """
    Posts telemetry data to the API with buffering and retry.

    Features:
    - Buffered posting (batch multiple frames)
    - Automatic retry on failure
    - Circuit breaker for API
    """

    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        buffer_size: int = 10,
        flush_interval_sec: float = 5.0,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.buffer_size = buffer_size
        self.flush_interval_sec = flush_interval_sec

        self._buffer: List[Dict[str, Any]] = []
        self._last_flush = time.time()

        # Circuit breaker for API
        self.circuit = CircuitBreaker(
            name="api_poster",
            failure_threshold=5,
            success_threshold=2,
            timeout_sec=60.0,
        )

    def add_frame(self, frame: TelemetryFrame) -> None:
        """Add a frame to the buffer."""
        for signal_name, value in frame.signals.items():
            self._buffer.append({
                "timestamp": frame.timestamp,
                "signal": signal_name,
                "value": value,
                "quality": frame.quality,
            })

    def should_flush(self) -> bool:
        """Check if buffer should be flushed."""
        if len(self._buffer) >= self.buffer_size:
            return True
        if time.time() - self._last_flush >= self.flush_interval_sec:
            return True
        return False

    def flush(self) -> bool:
        """Flush buffer to API."""
        if not self._buffer:
            return True

        if not self.circuit.can_execute():
            logger.warning("API circuit is open, skipping flush")
            return False

        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.post(
                self.api_url,
                json=self._buffer,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            logger.debug(f"Flushed {len(self._buffer)} telemetry points to API")
            self._buffer.clear()
            self._last_flush = time.time()
            self.circuit.record_success()
            return True

        except Exception as e:
            logger.error(f"Failed to flush to API: {e}")
            self.circuit.record_failure(e)
            return False


class TelemetryService:
    """
    Main telemetry service that coordinates collection and posting.

    Usage:
        service = TelemetryService.from_config(site_config)
        await service.run()
    """

    def __init__(
        self,
        collector: ModbusCollector,
        poster: Optional[ApiPoster] = None,
        poll_interval_sec: float = 1.0,
        on_frame: Optional[Callable[[TelemetryFrame], None]] = None,
    ):
        self.collector = collector
        self.poster = poster
        self.poll_interval_sec = poll_interval_sec
        self.on_frame = on_frame

        self._running = False
        self._frames_collected = 0
        self._frames_posted = 0

    @classmethod
    def from_config(
        cls,
        config: SiteConfig,
        on_frame: Optional[Callable[[TelemetryFrame], None]] = None,
    ) -> "TelemetryService":
        """Create service from site configuration."""
        telemetry_cfg = config.telemetry

        # Create collector
        collector = ModbusCollector(
            host=telemetry_cfg.modbus_host or "127.0.0.1",
            port=telemetry_cfg.modbus_port,
        )

        # Create poster if API URL configured
        poster = None
        if telemetry_cfg.api_url:
            poster = ApiPoster(
                api_url=telemetry_cfg.api_url,
                api_key=telemetry_cfg.api_key,
            )

        return cls(
            collector=collector,
            poster=poster,
            poll_interval_sec=telemetry_cfg.poll_interval_sec,
            on_frame=on_frame,
        )

    async def run(self) -> None:
        """Run the telemetry collection loop."""
        self._running = True
        logger.info(
            f"Starting telemetry service, polling every {self.poll_interval_sec}s"
        )

        try:
            await self.collector.connect()

            while self._running:
                # Collect frame
                frame = await self.collector.read_all()
                self._frames_collected += 1

                # Call frame callback
                if self.on_frame:
                    try:
                        self.on_frame(frame)
                    except Exception as e:
                        logger.error(f"Error in frame callback: {e}")

                # Buffer for posting
                if self.poster:
                    self.poster.add_frame(frame)

                    # Flush if needed
                    if self.poster.should_flush():
                        if self.poster.flush():
                            self._frames_posted += len(frame.signals)

                # Wait for next poll
                await asyncio.sleep(self.poll_interval_sec)

        except asyncio.CancelledError:
            logger.info("Telemetry service cancelled")
        finally:
            await self.collector.disconnect()
            if self.poster:
                self.poster.flush()  # Final flush
            self._running = False

    def stop(self) -> None:
        """Stop the telemetry service."""
        self._running = False
        logger.info("Stopping telemetry service")

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "frames_collected": self._frames_collected,
            "frames_posted": self._frames_posted,
            "running": self._running,
            "collector_connected": self.collector._connected,
            "collector_circuit_state": self.collector.circuit.state.value,
            "poster_circuit_state": self.poster.circuit.state.value if self.poster else None,
        }
