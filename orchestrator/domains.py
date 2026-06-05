"""Domain abstraction: base class and registry for all monitoring domains."""

import importlib
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Domain(ABC):
    """Abstract base class for all monitoring domains.

    Subclasses implement observe() and analyze() and declare
    interval_seconds.  The orchestrator calls should_run() each cycle
    and invokes analyze() when it returns True.
    """

    name: str = ""
    interval_seconds: int = 60
    enabled: bool = True

    def __init__(self, config: dict) -> None:
        self.config = config
        self._last_run: Optional[float] = None
        self._logger = logging.getLogger(f"domain.{self.name}")

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def should_run(self) -> bool:
        """Return True when the domain is due for another cycle."""
        if not self.enabled:
            return False
        if self._last_run is None:
            return True
        elapsed = time.monotonic() - self._last_run
        return elapsed >= self.interval_seconds

    def mark_ran(self) -> None:
        self._last_run = time.monotonic()

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    @abstractmethod
    def observe(self) -> dict:
        """Collect raw metrics from the target system."""

    @abstractmethod
    def analyze(self) -> dict:
        """Run analysis over observations and return structured insights."""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class DomainRegistry:
    """Loads and instantiates domain classes declared in config YAML.

    Config structure expected under the ``domains`` key::

        domains:
          capacity:
            enabled: true
            class: CapacityDomain
            module: orchestrator.capacity_domain
            interval_seconds: 60
            tools: [capacity_forecaster, storage_advisor]
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._domains: dict[str, Domain] = {}

    def load(self) -> list[Domain]:
        """Instantiate all enabled domains and return them."""
        domains_cfg = self._config.get("domains", {})
        if not domains_cfg:
            logger.warning("No domains found in config")
            return []

        loaded: list[Domain] = []
        for domain_name, cfg in domains_cfg.items():
            if not cfg.get("enabled", True):
                logger.info("Domain %s is disabled — skipping", domain_name)
                continue
            try:
                instance = self._load_domain(domain_name, cfg)
                self._domains[domain_name] = instance
                loaded.append(instance)
                logger.info(
                    "Loaded domain '%s' (interval=%ss)",
                    domain_name,
                    cfg.get("interval_seconds", instance.interval_seconds),
                )
            except Exception as exc:
                logger.error("Failed to load domain '%s': %s", domain_name, exc, exc_info=True)

        return loaded

    def _load_domain(self, domain_name: str, cfg: dict) -> Domain:
        module_path = cfg.get("module")
        class_name = cfg.get("class")
        if not module_path or not class_name:
            raise ValueError(
                f"Domain '{domain_name}' must specify 'module' and 'class' in config"
            )
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        # Merge domain-level config so each domain has interval / tools etc.
        domain_cfg = {**self._config, "domain": cfg}
        instance: Domain = cls(domain_cfg)
        # Override interval from config if provided
        if "interval_seconds" in cfg:
            instance.interval_seconds = cfg["interval_seconds"]
        instance.name = domain_name
        return instance

    def get(self, name: str) -> Optional[Domain]:
        return self._domains.get(name)

    def all(self) -> list[Domain]:
        return list(self._domains.values())
