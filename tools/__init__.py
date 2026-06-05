"""Tool abstraction layer.

Each Tool is a stateless unit of work invoked by a domain.  Tools declare:
- capability_tags  — semantic labels used by the registry for discovery
- timeout_seconds  — maximum allowed runtime
- depends_on       — list of tool names that must run first (for topological sort)

Domains compose tools via ToolRegistry.resolve_execution_order() to obtain a
DAG-ordered list, then call tool.run(input_dict) in sequence, threading
outputs forward.
"""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Abstract base class for all monitoring tools.

    Subclasses must implement ``run()`` and declare class-level
    ``capability_tags``, ``timeout_seconds``, and ``depends_on``.
    """

    capability_tags: list[str] = []
    timeout_seconds: int = 5
    depends_on: list[str] = []

    @abstractmethod
    def run(self, input_data: dict) -> dict:
        """Execute the tool with the given input and return a result dict.

        Parameters
        ----------
        input_data:
            Arbitrary key/value pairs passed from the domain or a prior tool.

        Returns
        -------
        dict
            Tool-specific result; merged into the pipeline context by the
            domain before being passed to downstream tools.
        """
