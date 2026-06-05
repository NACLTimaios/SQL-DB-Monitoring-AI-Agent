"""ToolRegistry: loads, resolves, and dispatches tool instances from config."""

import importlib
import logging
from collections import defaultdict, deque
from typing import Any

from tools import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Manages tool discovery and execution-order resolution.

    Config structure expected under the ``tools`` key::

        tools:
          capacity_forecaster:
            module: tools.capacity_tools
            class: CapacityForecaster
            capability_tags: [forecasting, trending]
            depends_on: []
            timeout_seconds: 2
          storage_advisor:
            module: tools.capacity_tools
            class: StorageAdvisor
            depends_on: [capacity_forecaster]
            timeout_seconds: 1
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._tools: dict[str, Tool] = {}
        self._tool_cfg: dict[str, dict] = {}
        self._load_all()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_tools(self, domain: str) -> list[Tool]:
        """Return all tools declared for *domain* in config.

        Parameters
        ----------
        domain:
            Domain name as it appears under ``domains.<name>.tools`` in YAML.
        """
        domain_cfg = self._config.get("domains", {}).get(domain, {})
        tool_names: list[str] = domain_cfg.get("tools", [])
        result: list[Tool] = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool is None:
                logger.warning("Tool '%s' not found for domain '%s'", name, domain)
                continue
            result.append(tool)
        return result

    def resolve_execution_order(self, domain: str) -> list[Tool]:
        """Return tools for *domain* sorted via topological order on depends_on.

        Topological sort (Kahn's algorithm):
        1. Build an adjacency list: edge A→B means A must run before B.
        2. Compute in-degree for each node in the subgraph.
        3. Process nodes with in-degree 0 first; decrement neighbours.
        4. If any node is never processed the graph contains a cycle — raise.

        Parameters
        ----------
        domain:
            Domain name key from config.

        Returns
        -------
        list[Tool]
            Tools in safe execution order (dependencies before dependants).

        Raises
        ------
        ValueError
            If a dependency cycle is detected among the domain's tools.
        """
        domain_cfg = self._config.get("domains", {}).get(domain, {})
        tool_names: list[str] = domain_cfg.get("tools", [])

        # Build subgraph limited to this domain's tool set.
        tool_set = set(tool_names)
        in_degree: dict[str, int] = {n: 0 for n in tool_set}
        dependants: dict[str, list[str]] = defaultdict(list)

        for name in tool_names:
            cfg = self._tool_cfg.get(name, {})
            for dep in cfg.get("depends_on", []):
                if dep not in tool_set:
                    continue
                in_degree[name] += 1
                dependants[dep].append(name)

        queue: deque[str] = deque(n for n in tool_names if in_degree[n] == 0)
        ordered: list[str] = []

        while queue:
            node = queue.popleft()
            ordered.append(node)
            for neighbour in dependants[node]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        if len(ordered) != len(tool_names):
            cyclic = [n for n in tool_names if n not in ordered]
            raise ValueError(
                f"Dependency cycle detected among tools: {cyclic}"
            )

        result: list[Tool] = []
        for name in ordered:
            tool = self._tools.get(name)
            if tool:
                result.append(tool)
        return result

    def register_tool(self, name: str, class_name: str, module: str) -> None:
        """Dynamically register a tool by its fully-qualified module path.

        Parameters
        ----------
        name:
            Logical tool name (used in depends_on and domain configs).
        class_name:
            Python class name within *module*.
        module:
            Dotted module path, e.g. ``tools.capacity_tools``.
        """
        try:
            mod = importlib.import_module(module)
            cls = getattr(mod, class_name)
            self._tools[name] = cls()
            logger.info("Registered tool '%s' from %s.%s", name, module, class_name)
        except (ImportError, AttributeError) as exc:
            logger.error(
                "Cannot register tool '%s' (%s.%s): %s", name, module, class_name, exc
            )
            raise

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_names(self) -> list[str]:
        return list(self._tools.keys())

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        tools_cfg = self._config.get("tools", {})
        for tool_name, cfg in tools_cfg.items():
            module = cfg.get("module")
            class_name = cfg.get("class")
            if not module or not class_name:
                logger.warning(
                    "Tool '%s' missing 'module' or 'class' — skipping", tool_name
                )
                continue
            self._tool_cfg[tool_name] = cfg
            try:
                self.register_tool(tool_name, class_name, module)
            except Exception:
                pass  # error already logged in register_tool
