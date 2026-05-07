"""
KORA Production Service Runner

Main entry point for running the optimizer as a production service.

Features:
- Scheduled optimization runs
- Telemetry integration
- Health monitoring
- Graceful shutdown
- API integration
"""

from __future__ import annotations

import asyncio
import json
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests

from .config import SiteConfig, load_config
from .errors import (
    KoraError,
    SolverError,
    SolverTimeoutError,
    SolverInfeasibleError,
    create_error_report,
    safe_execute,
)
from .logging import (
    get_logger,
    setup_logging,
    log_optimizer_run,
    log_alert,
)
from .cache import get_cache, CacheConfig

logger = get_logger(__name__)


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    run_id: str
    site_id: str
    timestamp: datetime
    status: str  # "success", "timeout", "infeasible", "error"
    solve_time_sec: float

    # Solution metrics (if successful)
    curtailment_rate: Optional[float] = None
    total_revenue: Optional[float] = None
    total_curtailment_kwh: Optional[float] = None
    total_demand_served_kwh: Optional[float] = None
    blackout_hours: int = 0

    # Price schedule (if successful)
    price_schedule: Optional[List[float]] = None
    battery_schedule: Optional[Dict[str, List[float]]] = None

    # Error info (if failed)
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "site_id": self.site_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "solve_time_sec": self.solve_time_sec,
            "curtailment_rate": self.curtailment_rate,
            "total_revenue": self.total_revenue,
            "total_curtailment_kwh": self.total_curtailment_kwh,
            "total_demand_served_kwh": self.total_demand_served_kwh,
            "blackout_hours": self.blackout_hours,
            "price_schedule": self.price_schedule,
            "battery_schedule": self.battery_schedule,
            "error_message": self.error_message,
            "error_type": self.error_type,
        }

    @property
    def is_success(self) -> bool:
        return self.status == "success"


class OptimizerRunner:
    """
    Runs the optimization model with production error handling.
    """

    def __init__(self, config: SiteConfig, cache_enabled: bool = True):
        self.config = config
        self._last_run: Optional[OptimizationResult] = None
        self._run_count = 0
        self._success_count = 0
        self._cache_hits = 0
        self._cache = get_cache() if cache_enabled else None

    def run(
        self,
        pv_forecast: List[float],
        demand_forecast: List[float],
        initial_soc_kwh: Optional[float] = None,
    ) -> OptimizationResult:
        """
        Run the optimizer with the given forecasts.

        Args:
            pv_forecast: Hourly PV production forecast (kW)
            demand_forecast: Hourly demand forecast (kW)
            initial_soc_kwh: Initial battery state of charge

        Returns:
            OptimizationResult with solution or error info
        """
        run_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        self._run_count += 1

        logger.info(
            f"Starting optimization run {run_id}",
            extra={
                "run_id": run_id,
                "site_id": self.config.site_id,
                "horizon": len(pv_forecast),
            },
        )

        # Check cache first
        cache_key_inputs = {
            "site_id": self.config.site_id,
            "pv_forecast": pv_forecast,
            "demand_forecast": demand_forecast,
            "initial_soc_kwh": initial_soc_kwh,
            "battery_capacity_kwh": self.config.battery.capacity_kwh,
            "battery_power_kw": self.config.battery.power_kw,
        }

        if self._cache:
            cache_key = self._cache.compute_key(cache_key_inputs)
            cached_result = self._cache.get(cache_key)
            if cached_result:
                self._cache_hits += 1
                logger.info(f"Cache hit for run {run_id}")
                # Reconstruct OptimizationResult from cached data
                result = OptimizationResult(
                    run_id=run_id,
                    site_id=self.config.site_id,
                    timestamp=datetime.utcnow(),
                    status=cached_result["status"],
                    solve_time_sec=0.0,  # No solve time for cached results
                    curtailment_rate=cached_result.get("curtailment_rate"),
                    total_revenue=cached_result.get("total_revenue"),
                    total_curtailment_kwh=cached_result.get("total_curtailment_kwh"),
                    total_demand_served_kwh=cached_result.get("total_demand_served_kwh"),
                    blackout_hours=cached_result.get("blackout_hours", 0),
                    price_schedule=cached_result.get("price_schedule"),
                    battery_schedule=cached_result.get("battery_schedule"),
                )
                self._last_run = result
                return result

        try:
            # Import here to avoid circular imports
            # Use Gurobi-based model (with automatic HiGHS fallback)
            from optimizer.gurobi_model import (
                KoraOptimizerInputs,
                solve_kora_model,
                extract_kora_solution,
                calculate_metrics,
            )

            # Build inputs from config
            inputs = KoraOptimizerInputs(
                pv_forecast_kw=pv_forecast,
                base_demand_kw=demand_forecast,
                battery_capacity_kwh=self.config.battery.capacity_kwh,
                battery_power_kw=self.config.battery.power_kw,
                soc_init_kwh=initial_soc_kwh or self.config.battery.soc_min_kwh * 1.5,
                soc_min_kwh=self.config.battery.soc_min_kwh,
                soc_max_kwh=self.config.battery.soc_max_kwh,
                eta_charge=self.config.battery.efficiency_charge,
                eta_discharge=self.config.battery.efficiency_discharge,
                battery_cycle_cost_per_kwh=self.config.battery.cycle_cost_per_kwh,
                price_min=self.config.pricing.min_price,
                price_max=self.config.pricing.max_price,
                price_reference=self.config.pricing.reference_price,
                demand_elasticity=self.config.demand.elasticity,
                curtailment_value_per_kwh=self.config.optimizer.curtailment_penalty,
                blackout_penalty_per_kwh=self.config.optimizer.blackout_penalty,
                timestep_hours=self.config.optimizer.timestep_hours,
            )

            # Solve
            model = solve_kora_model(
                inputs,
                solver=self.config.optimizer.solver,
                time_limit_sec=self.config.optimizer.time_limit_sec,
            )

            # Extract solution
            solution = extract_kora_solution(model)
            metrics = calculate_metrics(solution, inputs)

            solve_time = time.time() - start_time
            self._success_count += 1

            result = OptimizationResult(
                run_id=run_id,
                site_id=self.config.site_id,
                timestamp=datetime.utcnow(),
                status="success",
                solve_time_sec=solve_time,
                curtailment_rate=metrics["curtailment_rate"],
                total_revenue=metrics["total_revenue_ariary"],
                total_curtailment_kwh=metrics["total_curtail_kwh"],
                total_demand_served_kwh=metrics["total_demand_served_kwh"],
                blackout_hours=metrics["blackout_hours"],
                price_schedule=solution["price_ariary"],
                battery_schedule={
                    "charge_kw": solution["p_charge_kw"],
                    "discharge_kw": solution["p_discharge_kw"],
                    "soc_kwh": solution["soc_kwh"],
                },
            )

            log_optimizer_run(
                logger,
                site_id=self.config.site_id,
                horizon_hours=len(pv_forecast),
                solver=self.config.optimizer.solver,
                status="success",
                solve_time_sec=solve_time,
                curtailment_rate=metrics["curtailment_rate"],
                revenue=metrics["total_revenue_ariary"],
            )

            # Cache the successful result
            if self._cache:
                cache_data = {
                    "status": "success",
                    "curtailment_rate": result.curtailment_rate,
                    "total_revenue": result.total_revenue,
                    "total_curtailment_kwh": result.total_curtailment_kwh,
                    "total_demand_served_kwh": result.total_demand_served_kwh,
                    "blackout_hours": result.blackout_hours,
                    "price_schedule": result.price_schedule,
                    "battery_schedule": result.battery_schedule,
                }
                self._cache.set(cache_key, cache_data)
                logger.debug(f"Cached optimization result with key {cache_key}")

            self._last_run = result
            return result

        except Exception as e:
            solve_time = time.time() - start_time

            # Determine error type
            if "timeout" in str(e).lower() or "time limit" in str(e).lower():
                status = "timeout"
                error_type = "SolverTimeoutError"
            elif "infeasible" in str(e).lower():
                status = "infeasible"
                error_type = "SolverInfeasibleError"
            else:
                status = "error"
                error_type = type(e).__name__

            result = OptimizationResult(
                run_id=run_id,
                site_id=self.config.site_id,
                timestamp=datetime.utcnow(),
                status=status,
                solve_time_sec=solve_time,
                error_message=str(e),
                error_type=error_type,
            )

            log_optimizer_run(
                logger,
                site_id=self.config.site_id,
                horizon_hours=len(pv_forecast),
                solver=self.config.optimizer.solver,
                status=status,
                solve_time_sec=solve_time,
            )

            logger.error(f"Optimization failed: {e}", exc_info=True)

            self._last_run = result
            return result

    def get_stats(self) -> Dict[str, Any]:
        """Get runner statistics."""
        stats = {
            "total_runs": self._run_count,
            "successful_runs": self._success_count,
            "success_rate": self._success_count / self._run_count if self._run_count > 0 else 0,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": self._cache_hits / self._run_count if self._run_count > 0 else 0,
            "last_run": self._last_run.to_dict() if self._last_run else None,
        }
        if self._cache:
            stats["cache_stats"] = self._cache.stats()
        return stats


class KoraService:
    """
    Main Kora service that coordinates all components.

    This is the primary entry point for running Kora in production.
    """

    def __init__(
        self,
        config: SiteConfig,
        api_url: Optional[str] = None,
        run_interval_minutes: int = 15,
        cache_enabled: bool = True,
    ):
        self.config = config
        self.api_url = api_url
        self.run_interval_minutes = run_interval_minutes

        self.runner = OptimizerRunner(config, cache_enabled=cache_enabled)

        self._running = False
        self._start_time: Optional[datetime] = None
        self._last_result: Optional[OptimizationResult] = None

        # Forecast providers (can be overridden)
        self._pv_forecast_provider: Optional[Callable[[], List[float]]] = None
        self._demand_forecast_provider: Optional[Callable[[], List[float]]] = None

    def set_forecast_providers(
        self,
        pv_provider: Callable[[], List[float]],
        demand_provider: Callable[[], List[float]],
    ) -> None:
        """Set custom forecast providers."""
        self._pv_forecast_provider = pv_provider
        self._demand_forecast_provider = demand_provider

    def _get_forecasts(self) -> tuple[List[float], List[float]]:
        """Get PV and demand forecasts."""
        if self._pv_forecast_provider and self._demand_forecast_provider:
            return self._pv_forecast_provider(), self._demand_forecast_provider()

        # Default: generate synthetic forecasts
        from mahavelona_config import (
            generate_madagascar_solar_profile,
            generate_madagascar_demand_profile,
            MahavelonaSpecs,
        )

        specs = MahavelonaSpecs()
        pv = generate_madagascar_solar_profile(
            peak_capacity_kw=self.config.solar.capacity_kw,
            hours=self.config.optimizer.horizon_hours,
        )
        demand = generate_madagascar_demand_profile(
            total_customers=251,
            peak_load_kw=self.config.demand.peak_load_kw,
            hours=self.config.optimizer.horizon_hours,
        )
        return pv.tolist(), demand.tolist()

    def _post_result(self, result: OptimizationResult) -> bool:
        """Post optimization result to API."""
        if not self.api_url:
            return True

        try:
            response = requests.post(
                f"{self.api_url}/kora/optimization-result",
                json=result.to_dict(),
                timeout=10,
            )
            response.raise_for_status()
            logger.debug("Posted optimization result to API")
            return True
        except Exception as e:
            logger.error(f"Failed to post result to API: {e}")
            return False

    def _check_alerts(self, result: OptimizationResult) -> None:
        """Check for alert conditions."""
        if not result.is_success:
            if self.config.alerts.alert_on_solver_failure:
                log_alert(
                    logger,
                    site_id=self.config.site_id,
                    alert_type="solver_failure",
                    message=f"Optimization failed: {result.error_message}",
                    severity="error",
                    data={"run_id": result.run_id, "error_type": result.error_type},
                )

        elif result.curtailment_rate is not None:
            threshold = self.config.alerts.curtailment_threshold_percent / 100
            if result.curtailment_rate > threshold:
                if self.config.alerts.alert_on_high_curtailment:
                    log_alert(
                        logger,
                        site_id=self.config.site_id,
                        alert_type="high_curtailment",
                        message=f"Curtailment rate {result.curtailment_rate*100:.1f}% exceeds threshold",
                        severity="warning",
                        data={
                            "run_id": result.run_id,
                            "curtailment_rate": result.curtailment_rate,
                            "threshold": threshold,
                        },
                    )

    async def run_once(self) -> OptimizationResult:
        """Run a single optimization."""
        pv_forecast, demand_forecast = self._get_forecasts()
        result = self.runner.run(pv_forecast, demand_forecast)

        self._last_result = result
        self._post_result(result)
        self._check_alerts(result)

        return result

    async def run(self) -> None:
        """Run the service continuously."""
        self._running = True
        self._start_time = datetime.utcnow()

        logger.info(
            f"Starting Kora service for site {self.config.site_id}",
            extra={
                "site_id": self.config.site_id,
                "run_interval_minutes": self.run_interval_minutes,
            },
        )

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.stop)

        try:
            while self._running:
                # Run optimization
                await self.run_once()

                # Wait for next run
                await asyncio.sleep(self.run_interval_minutes * 60)

        except asyncio.CancelledError:
            logger.info("Service cancelled")
        finally:
            self._running = False
            logger.info("Kora service stopped")

    def stop(self) -> None:
        """Stop the service gracefully."""
        logger.info("Stopping Kora service...")
        self._running = False

    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        uptime = None
        if self._start_time:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()

        return {
            "site_id": self.config.site_id,
            "running": self._running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": uptime,
            "run_interval_minutes": self.run_interval_minutes,
            "runner_stats": self.runner.get_stats(),
            "last_result": self._last_result.to_dict() if self._last_result else None,
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        healthy = True
        checks = {}

        # Check if service is running
        checks["service_running"] = self._running
        if not self._running:
            healthy = False

        # Check last run status
        if self._last_result:
            checks["last_run_success"] = self._last_result.is_success
            if not self._last_result.is_success:
                healthy = False

            # Check if last run was recent
            age = (datetime.utcnow() - self._last_result.timestamp).total_seconds()
            max_age = self.run_interval_minutes * 60 * 2  # Allow 2x interval
            checks["last_run_recent"] = age < max_age
            if age >= max_age:
                healthy = False

        return {
            "healthy": healthy,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        }


def main():
    """Main entry point for the Kora service."""
    import argparse

    parser = argparse.ArgumentParser(description="KORA Optimizer Service")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to site configuration YAML file",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Log file path",
    )
    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Output JSON formatted logs",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run optimization once and exit",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Minutes between optimization runs",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="API URL for posting results",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable result caching",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(
        level=args.log_level,
        json_output=args.json_logs,
        log_file=args.log_file,
    )

    # Load configuration
    try:
        config = load_config(args.config)
        logger.info(f"Loaded configuration for site: {config.site_name}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Create and run service
    service = KoraService(
        config=config,
        api_url=args.api_url,
        run_interval_minutes=args.interval,
        cache_enabled=not args.no_cache,
    )

    if args.run_once:
        # Single run mode
        result = asyncio.run(service.run_once())
        print(json.dumps(result.to_dict(), indent=2))
        sys.exit(0 if result.is_success else 1)
    else:
        # Continuous mode
        asyncio.run(service.run())


if __name__ == "__main__":
    main()
