"""CLI entry-point for the SQL monitoring agent.

Usage examples::

    python main.py run
    python main.py init-db
    python main.py validate-config --config config.yaml
    python main.py status
    python main.py test-domain --domain capacity
    python main.py test-tool --tool capacity_forecaster --input '{"disk_free_gb": 50, "trend_gb_per_day": 1.5}'
"""

import json
import logging
import sys
import threading
from pathlib import Path

import click
from dotenv import load_dotenv

# Load environment variables from .env file at startup
load_dotenv(Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _load_config(config_path: str) -> dict:
    from config.loader import ConfigLoader

    loader = ConfigLoader()
    return loader.load(config_path)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def cli():
    """SQL database monitoring agent — management CLI."""


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@cli.command("run")
@click.option("--config", default="config.yaml", show_default=True, help="Path to config YAML")
@click.option("--log-level", default="INFO", show_default=True, help="Logging level")
def cmd_run(config: str, log_level: str) -> None:
    """Start the orchestrator and the API server together."""
    _setup_logging(log_level)
    logger = logging.getLogger(__name__)

    try:
        from api.server import _state, app, _handle_sigterm
        import signal
        import uvicorn
        from store import get_engine, get_session, init_db

        cfg = _load_config(config)
        db_cfg = cfg["database"]
        db_url = (
            f"postgresql://{db_cfg['user']}:{db_cfg['password']}"
            f"@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['database']}"
        )
        engine = get_engine(db_url)
        init_db(engine)

        _state["config"] = cfg
        _state["config_path"] = config
        _state["engine"] = engine
        _state["session_factory"] = get_session(engine)

        signal.signal(signal.SIGTERM, _handle_sigterm)

        api_cfg = cfg.get("api", {})
        host = api_cfg.get("host", "0.0.0.0")
        port = int(api_cfg.get("port", 8080))

        logger.info("Starting agent on %s:%s", host, port)
        uvicorn.run(app, host=host, port=port, log_level=log_level.lower())
    except Exception as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# init-db
# ---------------------------------------------------------------------------


@cli.command("init-db")
@click.option("--config", default="config.yaml", show_default=True)
def cmd_init_db(config: str) -> None:
    """Create the database schema (idempotent)."""
    _setup_logging("INFO")
    try:
        from store import get_engine, init_db

        cfg = _load_config(config)
        db_cfg = cfg["database"]
        db_url = (
            f"postgresql://{db_cfg['user']}:{db_cfg['password']}"
            f"@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['database']}"
        )
        engine = get_engine(db_url)
        init_db(engine)
        click.echo("Database schema initialised successfully.")
    except Exception as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# validate-config
# ---------------------------------------------------------------------------


@cli.command("validate-config")
@click.option("--config", default="config.yaml", show_default=True)
def cmd_validate_config(config: str) -> None:
    """Validate config.yaml syntax and required structure."""
    _setup_logging("WARNING")
    try:
        cfg = _load_config(config)
        domain_names = list(cfg.get("domains", {}).keys())
        tool_names = list(cfg.get("tools", {}).keys())
        click.echo(f"Config valid. Domains: {domain_names}. Tools: {tool_names}.")
    except Exception as exc:
        click.echo(f"Config INVALID: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@cli.command("status")
@click.option("--config", default="config.yaml", show_default=True)
def cmd_status(config: str) -> None:
    """Show DB health and orchestrator status."""
    _setup_logging("WARNING")
    try:
        from store import check_db_health, get_engine

        cfg = _load_config(config)
        db_cfg = cfg["database"]
        db_url = (
            f"postgresql://{db_cfg['user']}:{db_cfg['password']}"
            f"@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['database']}"
        )
        engine = get_engine(db_url)
        db_ok = check_db_health(engine)
        click.echo(f"Database reachable:  {'YES' if db_ok else 'NO'}")
        click.echo("Orchestrator:        not running (use 'run' command)")
    except Exception as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# test-domain
# ---------------------------------------------------------------------------


@cli.command("test-domain")
@click.option("--config", default="config.yaml", show_default=True)
@click.option("--domain", required=True, help="Domain name (e.g. capacity)")
def cmd_test_domain(config: str, domain: str) -> None:
    """Run a single domain once and print the result."""
    _setup_logging("INFO")
    try:
        from orchestrator.domains import DomainRegistry

        cfg = _load_config(config)
        registry = DomainRegistry(cfg)
        domains = registry.load()
        target = next((d for d in domains if d.name == domain), None)
        if target is None:
            raise ValueError(
                f"Domain '{domain}' not found. Available: {[d.name for d in domains]}"
            )
        result = target.analyze()
        click.echo(json.dumps(result, indent=2, default=str))
    except Exception as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# test-tool
# ---------------------------------------------------------------------------


@cli.command("test-tool")
@click.option("--config", default="config.yaml", show_default=True)
@click.option("--tool", "tool_name", required=True, help="Tool name (e.g. capacity_forecaster)")
@click.option("--input", "input_json", default="{}", show_default=True, help="JSON input dict")
def cmd_test_tool(config: str, tool_name: str, input_json: str) -> None:
    """Run a single tool with the given JSON input and print the result."""
    _setup_logging("INFO")
    try:
        from tools.registry import ToolRegistry

        cfg = _load_config(config)
        registry = ToolRegistry(cfg)
        tool = registry.get(tool_name)
        if tool is None:
            raise ValueError(
                f"Tool '{tool_name}' not found. Available: {registry.all_names()}"
            )
        input_data = json.loads(input_json)
        result = tool.run(input_data)
        click.echo(json.dumps(result, indent=2, default=str))
    except json.JSONDecodeError as exc:
        click.echo(f"Invalid JSON input: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
