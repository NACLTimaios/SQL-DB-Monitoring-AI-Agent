"""ConfigLoader: loads and validates the agent YAML configuration file."""

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Required top-level sections and their required sub-keys.
_REQUIRED_SECTIONS: dict[str, list[str]] = {
    "domains": [],
    "tools": [],
    "database": ["host", "port", "database", "user", "password"],
    "api": ["host", "port"],
    "logging": ["level"],
}

_DOMAIN_REQUIRED_KEYS = ["enabled", "class", "module", "interval_seconds"]
_TOOL_REQUIRED_KEYS = ["module", "class"]


class ConfigLoader:
    """Loads a YAML config file, validates its structure, and returns a dict.

    Raises ``ValueError`` with descriptive messages when required keys are
    absent so operators can fix misconfiguration quickly.

    Usage::

        loader = ConfigLoader()
        config = loader.load("config.yaml")
    """

    def load(self, config_path: str) -> dict:
        """Load and validate the config at *config_path*.

        Parameters
        ----------
        config_path:
            Filesystem path to the YAML configuration file.

        Returns
        -------
        dict
            Fully validated configuration dictionary.

        Raises
        ------
        FileNotFoundError
            If *config_path* does not exist.
        ValueError
            If the configuration is structurally invalid.
        yaml.YAMLError
            If the file contains invalid YAML.
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with path.open("r") as fh:
            raw = yaml.safe_load(fh)

        if not isinstance(raw, dict):
            raise ValueError(f"Config file must be a YAML mapping, got {type(raw).__name__}")

        # Resolve environment variables in configuration
        raw = self._resolve_env_vars(raw)

        self._validate(raw)
        logger.info("Configuration loaded from %s", config_path)
        return raw

    def _resolve_env_vars(self, config: Any) -> Any:
        """Recursively resolve ${VAR_NAME} patterns with environment variables.

        Supports format: ${VAR_NAME} or ${VAR_NAME:default_value}
        """
        if isinstance(config, dict):
            return {k: self._resolve_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Replace ${VAR_NAME} with environment variable value
            def replace_env(match):
                var_spec = match.group(1)
                if ':' in var_spec:
                    var_name, default = var_spec.split(':', 1)
                    return os.environ.get(var_name.strip(), default.strip())
                else:
                    var_name = var_spec.strip()
                    value = os.environ.get(var_name)
                    if value is None:
                        raise ValueError(
                            f"Environment variable '{var_name}' is required but not set. "
                            f"Set it before starting the application: export {var_name}=<value>"
                        )
                    return value

            return re.sub(r'\$\{([^}]+)\}', replace_env, config)
        else:
            return config

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate(self, config: dict) -> None:
        self._validate_top_level(config)
        self._validate_domains(config.get("domains", {}))
        self._validate_tools(config.get("tools", {}))
        self._validate_database(config.get("database", {}))
        self._validate_api(config.get("api", {}))

    def _validate_top_level(self, config: dict) -> None:
        for section, required_keys in _REQUIRED_SECTIONS.items():
            if section not in config:
                raise ValueError(f"Missing required config section: '{section}'")
            section_cfg = config[section]
            for key in required_keys:
                if key not in section_cfg:
                    raise ValueError(
                        f"Missing required key '{key}' in config section '{section}'"
                    )

    def _validate_domains(self, domains: dict) -> None:
        if not domains:
            logger.warning("No domains defined in config")
            return
        for name, cfg in domains.items():
            if not isinstance(cfg, dict):
                raise ValueError(f"Domain '{name}' config must be a mapping")
            for key in _DOMAIN_REQUIRED_KEYS:
                if key not in cfg:
                    raise ValueError(
                        f"Domain '{name}' is missing required key: '{key}'"
                    )

    def _validate_tools(self, tools: dict) -> None:
        if not tools:
            logger.warning("No tools defined in config")
            return
        for name, cfg in tools.items():
            if not isinstance(cfg, dict):
                raise ValueError(f"Tool '{name}' config must be a mapping")
            for key in _TOOL_REQUIRED_KEYS:
                if key not in cfg:
                    raise ValueError(
                        f"Tool '{name}' is missing required key: '{key}'"
                    )

    def _validate_database(self, db_cfg: dict) -> None:
        port = db_cfg.get("port")
        if port is not None and not isinstance(port, int):
            raise ValueError(
                f"database.port must be an integer, got {type(port).__name__}"
            )

    def _validate_api(self, api_cfg: dict) -> None:
        port = api_cfg.get("port")
        if port is not None and not isinstance(port, int):
            raise ValueError(
                f"api.port must be an integer, got {type(port).__name__}"
            )
