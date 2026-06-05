"""Orchestrator: main run-loop that drives all domains on their schedules."""

import logging
import signal
import time
from datetime import datetime, timezone
from typing import Optional

from config.loader import ConfigLoader
from orchestrator.aggregator import aggregate_insights
from orchestrator.domains import DomainRegistry
from orchestrator.hitl_generator import HITLGenerator
from store import get_engine, init_db, get_session

logger = logging.getLogger(__name__)


class Orchestrator:
    """Drives all monitoring domains and persists results.

    Usage::

        orchestrator = Orchestrator("config.yaml")
        orchestrator.run()
    """

    def __init__(self, config_path: str) -> None:
        loader = ConfigLoader()
        self._config = loader.load(config_path)
        self._running = False
        self._cycle_count = 0
        self._last_cycle_time: str | None = None

        # Set up storage.
        db_cfg = self._config.get("database", {})
        db_url = (
            f"postgresql://{db_cfg['user']}:{db_cfg['password']}"
            f"@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['database']}"
        )
        self._engine = get_engine(db_url)
        init_db(self._engine)
        self._session_factory = get_session(self._engine)

        # Load domains.
        self._registry = DomainRegistry(self._config)
        self._domains = self._registry.load()
        logger.info("Orchestrator initialised with %d domains", len(self._domains))

        # Wire SIGTERM handler.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Block and run the main loop until stopped."""
        self._running = True
        logger.info("Orchestrator starting main loop")
        while self._running:
            self._tick()
            time.sleep(1)

    def stop(self) -> None:
        """Request a graceful stop."""
        logger.info("Orchestrator stopping")
        self._running = False

    def run_once(self) -> dict:
        """Force-run all domains once and return aggregated result (for testing)."""
        results: dict = {}
        for domain in self._domains:
            try:
                result = domain.analyze()
                domain.mark_ran()
                results[domain.name] = result
            except Exception as exc:
                logger.error("Domain '%s' error: %s", domain.name, exc, exc_info=True)
                results[domain.name] = {"error": str(exc)}
        return aggregate_insights(results)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        cycle_start = time.monotonic()
        results: dict = {}

        for domain in self._domains:
            if not domain.should_run():
                continue
            try:
                t0 = time.monotonic()
                result = domain.analyze()
                elapsed = time.monotonic() - t0
                domain.mark_ran()
                results[domain.name] = result
                logger.debug(
                    "Domain '%s' completed in %.3fs", domain.name, elapsed
                )
            except Exception as exc:
                logger.error(
                    "Domain '%s' raised: %s", domain.name, exc, exc_info=True
                )
                results[domain.name] = {"error": str(exc)}

        if results:
            aggregated = aggregate_insights(results)
            self._cycle_count += 1
            self._last_cycle_time = datetime.now(timezone.utc).isoformat()
            cycle_elapsed = time.monotonic() - cycle_start
            logger.info(
                "Cycle #%d | status=%s | domains=%s | %.3fs",
                self._cycle_count,
                aggregated.get("status"),
                list(results.keys()),
                cycle_elapsed,
            )
            self._persist(results, aggregated)

    @staticmethod
    def _make_title(domain_name: str, result: dict) -> str:
        if domain_name == "locks":
            analysis = result.get("analysis", {})
            count = analysis.get("waiting_session_count", 0)
            risk = analysis.get("risk_level", "healthy").upper()
            if count > 0:
                chains = analysis.get("blocking_chains_count", 0)
                return f"Locks: {count} waiting session{'s' if count != 1 else ''}" + (
                    f", {chains} blocking chain{'s' if chains != 1 else ''}" if chains else ""
                ) + f" — {risk}"
            return "Locks: No contention"
        if domain_name == "capacity":
            obs = result.get("observations", {})
            forecast = result.get("forecast", {})
            size = obs.get("disk_size_gb", 0)
            days = forecast.get("days_remaining", 0)
            conns = obs.get("connections_active", 0)
            conns_max = obs.get("connections_max", 100)
            return f"Capacity: {size:.3f} GB used · {conns}/{conns_max} conns · {days} days to full"
        if domain_name == "performance":
            analysis = result.get("analysis", {})
            count = analysis.get("slow_query_count", 0)
            return f"Performance: {count} slow quer{'ies' if count != 1 else 'y'} detected"
        return f"{domain_name} cycle"

    def _persist(self, domain_results: dict, aggregated: dict) -> None:
        """Persist insights and HITL actions to the database."""
        from store.models import Insight
        from store.repository import Repository

        session = self._session_factory()
        repo = Repository(session)
        try:
            # Generate insights
            for domain_name, result in domain_results.items():
                if "error" in result:
                    continue
                import json as _json
                insight = Insight(
                    domain=domain_name,
                    title=self._make_title(domain_name, result),
                    description=_json.dumps(result, default=str),
                    severity=result.get("status", "info"),
                    status="pending",
                )
                repo.save_insight(insight)

            # Generate HITL actions based on domain results
            hitl_gen = HITLGenerator(repo)
            actions = hitl_gen.generate_actions_from_insights(domain_results)
            for action in actions:
                repo.save_action(action)
                logger.debug("Generated HITL action: %s", action.action_type)

            # Generate random synthetic issue for dashboard testing (10% chance)
            random_issue = hitl_gen.generate_random_issue()
            if random_issue:
                repo.save_action(random_issue)
                logger.debug("Generated random HITL issue: %s", random_issue.action_type)

            session.commit()
        except Exception as exc:
            logger.error("Failed to persist insights: %s", exc, exc_info=True)
            session.rollback()
        finally:
            session.close()

    def _handle_sigterm(self, signum: int, frame: object) -> None:
        logger.info("SIGTERM received — stopping orchestrator")
        self.stop()


# ---------------------------------------------------------------------------
# Direct entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    Orchestrator(config_path).run()
