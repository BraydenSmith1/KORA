"""
Modbus TCP polling collector for RTDS/RSCAD simulated microgrid.

Reads configured registers on a short interval and posts them to the Node API.
Non-blocking (asyncio) to keep reads timely.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import List, Optional

import requests
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.constants import Defaults
from pymodbus.exceptions import ModbusException


@dataclass
class Register:
    name: str
    address: int  # zero-based address
    unit: int = 1  # Modbus unit/slave id
    scale: float = 1.0
    kind: str = "holding"  # "holding" or "input"


@dataclass
class CollectorConfig:
    host: str = "127.0.0.1"
    port: int = Defaults.Port
    poll_interval_s: float = 1.0
    api_url: str = "http://localhost:3000/api/ingest"
    api_key: Optional[str] = None
    registers: List[Register] = None

    @staticmethod
    def from_json(path: str) -> "CollectorConfig":
        with open(path, "r") as f:
            raw = json.load(f)
        regs = [
            Register(
                name=r["name"],
                address=r["address"],
                unit=r.get("unit", 1),
                scale=r.get("scale", 1.0),
                kind=r.get("kind", "holding"),
            )
            for r in raw["registers"]
        ]
        return CollectorConfig(
            host=raw.get("host", "127.0.0.1"),
            port=raw.get("port", Defaults.Port),
            poll_interval_s=raw.get("poll_interval_s", 1.0),
            api_url=raw.get("api_url", "http://localhost:3000/api/ingest"),
            api_key=raw.get("api_key"),
            registers=regs,
        )


async def read_register(client: AsyncModbusTcpClient, reg: Register):
    try:
        if reg.kind == "holding":
            rr = await client.read_holding_registers(reg.address, 1, unit=reg.unit)
        else:
            rr = await client.read_input_registers(reg.address, 1, unit=reg.unit)
        if rr.isError():
            raise ModbusException(rr)
        return rr.registers[0] * reg.scale
    except Exception as exc:
        print(f"[WARN] Read failed {reg.name} @ {reg.address}: {exc}")
        return None


async def poll_loop(cfg: CollectorConfig):
    async with AsyncModbusTcpClient(cfg.host, port=cfg.port) as client:
        while True:
            ts = time.time()
            payload = []

            for reg in cfg.registers:
                val = await read_register(client, reg)
                if val is None:
                    continue
                payload.append(
                    {"timestamp": ts, "signal": reg.name, "value": val, "unit_id": reg.unit}
                )

            if payload:
                headers = {"Content-Type": "application/json"}
                if cfg.api_key:
                    headers["Authorization"] = f"Bearer {cfg.api_key}"
                try:
                    r = requests.post(cfg.api_url, json=payload, timeout=3, headers=headers)
                    r.raise_for_status()
                except Exception as exc:
                    print(f"[WARN] Failed to POST to API: {exc}")
            else:
                print("[INFO] No values read this cycle.")

            await asyncio.sleep(cfg.poll_interval_s)


def main():
    import argparse

    p = argparse.ArgumentParser(description="Modbus TCP collector for RTDS")
    p.add_argument("--config", type=str, default="python-optimizer/modbus_config.json", help="Path to JSON config")
    args = p.parse_args()

    cfg = CollectorConfig.from_json(args.config)
    print(f"Starting Modbus collector -> {cfg.host}:{cfg.port}, posting to {cfg.api_url}")
    try:
        asyncio.run(poll_loop(cfg))
    except KeyboardInterrupt:
        print("Stopping collector.")


if __name__ == "__main__":
    main()
