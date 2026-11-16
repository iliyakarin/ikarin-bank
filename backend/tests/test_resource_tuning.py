"""Tests for demo stack memory, thread, pool, and healthcheck resource tuning.

Verifies the configuration and runtime invariants across backend modules,
ClickHouse low-memory XML config, Dockerfile/entrypoint/requirements, Nginx,
.env.example, and docker-compose.prod.yml.
"""
import json
import re
import shlex
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

CLICKHOUSE_DISABLED_LOGS = (
    "asynchronous_metric_log",
    "metric_log",
    "trace_log",
    "text_log",
    "part_log",
    "query_thread_log",
    "processors_profile_log",
)

CLICKHOUSE_NUMERIC_CAPS = {
    "max_server_memory_usage": 536870912,
    "mark_cache_size": 67108864,
    "uncompressed_cache_size": 33554432,
    "background_schedule_pool_size": 16,
}

EXPECTED_MEMORY_LIMITS = {
    "postgres": "256M",
    "clickhouse": "768M",
    "kafka": "512M",
    "api": "384M",
    "proxy": "64M",
    "consumer": "192M",
    "outbox-worker": "128M",
    "sync-checker": "128M",
    "vendor-simulator": "128M",
    "vendor-simulator-db": "128M",
    "fed-gateway-db": "128M",
    "mock-fed-gateway": "128M",
    "deposit-funds-mock": "128M",
    "frontend": "256M",
    "scheduled-payments-worker": "128M",
    "financial-life-simulator": "128M",
    "cloudflared": "128M",
    "autoheal": "64M",
}

_DURATION_PART_RE = re.compile(r"(\d+(?:\.\d+)?)(ns|us|µs|ms|s|m|h)")
_DURATION_UNITS = {
    "ns": 1e-9,
    "us": 1e-6,
    "µs": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
}


def _parse_env(service: dict[str, Any]) -> dict[str, str]:
    """Normalize Docker Compose service environment (dict or KEY=VAL list)."""
    env = service.get("environment")
    if env is None:
        return {}
    if isinstance(env, dict):
        return {str(k): "" if v is None else str(v) for k, v in env.items()}
    if isinstance(env, list):
        parsed: dict[str, str] = {}
        for item in env:
            if not isinstance(item, str):
                raise TypeError(f"Unsupported environment list item: {item!r}")
            if "=" in item:
                key, value = item.split("=", 1)
                parsed[key] = value
            else:
                parsed[item] = ""
        return parsed
    raise TypeError(f"Unsupported environment type: {type(env)!r}")


def _command_tokens(service: dict[str, Any]) -> list[str]:
    """Return tokenized command arguments for string or list Compose commands."""
    cmd = service.get("command")
    if cmd is None:
        return []
    if isinstance(cmd, list):
        return [str(part) for part in cmd]
    if isinstance(cmd, str):
        return shlex.split(cmd)
    raise TypeError(f"Unsupported command type: {type(cmd)!r}")


def _has_flag_pair(tokens: list[str], flag: str, value: str) -> bool:
    """Return True if flag immediately precedes value in tokens."""
    return any(
        tokens[i] == flag and tokens[i + 1] == value
        for i in range(len(tokens) - 1)
    )


def _has_pg_param(tokens: list[str], key: str, value: str) -> bool:
    """Return True if Postgres config key=value is passed in command tokens."""
    target = f"{key}={value}"
    return any(tok in {target, f"-c{target}"} for tok in tokens)


def _healthcheck_command(service: dict[str, Any]) -> str:
    """Return flattened healthcheck test command string."""
    hc = service.get("healthcheck")
    if not isinstance(hc, dict):
        return ""
    test = hc.get("test")
    if isinstance(test, list):
        return " ".join(str(part) for part in test)
    if isinstance(test, str):
        return test
    return ""


def _parse_duration_seconds(value: str | int | float) -> float:
    """Parse Compose duration strings (e.g. '30s', '1m30s') into seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    parts = _DURATION_PART_RE.findall(text)
    if not parts or "".join(f"{num}{unit}" for num, unit in parts) != text:
        raise ValueError(f"Unsupported Compose duration format: {value!r}")
    return sum(float(num) * _DURATION_UNITS[unit] for num, unit in parts)


def _service_memory_limit(service: dict[str, Any]) -> str | None:
    """Extract deploy.resources.limits.memory if defined."""
    deploy = service.get("deploy") or {}
    resources = deploy.get("resources") or {}
    limits = resources.get("limits") or {}
    mem = limits.get("memory")
    return None if mem is None else str(mem).strip()


def _volume_mounts(service: dict[str, Any]) -> list[str]:
    """Normalize Compose short and long volume mount definitions to strings."""
    mounts: list[str] = []
    for entry in service.get("volumes") or []:
        if isinstance(entry, str):
            mounts.append(entry)
        elif isinstance(entry, dict) and "source" in entry and "target" in entry:
            mode = "ro" if entry.get("read_only") else "rw"
            mounts.append(f"{entry['source']}:{entry['target']}:{mode}")
    return mounts


@pytest.fixture(scope="module")
def compose_services() -> dict[str, dict[str, Any]]:
    """Load and return services mapping from docker-compose.prod.yml."""
    compose_path = REPO_ROOT / "docker-compose.prod.yml"
    data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "docker-compose.prod.yml must parse to a YAML mapping"
    services = data.get("services")
    assert isinstance(services, dict), "docker-compose.prod.yml must define a services mapping"
    return services


def test_database_engine_pool_limits():
    """Verify SQLAlchemy async engine caps pool_size=5 and max_overflow=5."""
    import database

    assert database.engine.pool.size() == 5
    assert database.engine.pool._max_overflow == 5


def test_kafka_session_timeout_tuned():
    """Verify OPTIMAL_SESSION_TIMEOUT is 30000ms in constants and consumer."""
    import constants
    import consumer

    assert constants.OPTIMAL_SESSION_TIMEOUT == 30000
    assert consumer.OPTIMAL_SESSION_TIMEOUT == 30000


def test_clickhouse_low_mem_xml():
    """Verify init-db/clickhouse-low-mem.xml disables profiling logs and caps memory/threads."""
    xml_path = REPO_ROOT / "init-db" / "clickhouse-low-mem.xml"
    assert xml_path.is_file(), f"Missing {xml_path}"

    root = ET.parse(xml_path).getroot()
    assert root.tag == "clickhouse", f"Expected <clickhouse> root tag, got <{root.tag}>"

    for table in CLICKHOUSE_DISABLED_LOGS:
        elem = root.find(table)
        assert elem is not None, f"Missing <{table}> element in {xml_path.name}"
        assert elem.attrib.get("remove") == "1", (
            f"<{table}> must set attribute remove=\"1\""
        )

    for tag, max_allowed in CLICKHOUSE_NUMERIC_CAPS.items():
        elem = root.find(tag)
        assert elem is not None and elem.text is not None, (
            f"Missing <{tag}> numeric setting in {xml_path.name}"
        )
        value = int(elem.text.strip())
        assert 0 < value <= max_allowed, (
            f"<{tag}> value {value} must be in (0, {max_allowed}]"
        )


def test_entrypoint_gates_migrations_behind_run_migrations():
    """Verify backend/entrypoint.sh gates alembic upgrade head on RUN_MIGRATIONS (default 1)."""
    entrypoint_text = (REPO_ROOT / "backend" / "entrypoint.sh").read_text(encoding="utf-8")
    gated_match = re.search(
        r'if\b[^\n]*\$\{RUN_MIGRATIONS:-1\}[^\n]*=\s*["\']?1["\']?.*?'
        r'\balembic\s+upgrade\s+head\b.*?\bfi\b',
        entrypoint_text,
        re.DOTALL,
    )
    assert gated_match is not None, (
        "backend/entrypoint.sh must gate 'alembic upgrade head' behind ${RUN_MIGRATIONS:-1} = 1"
    )


def test_dockerfile_cmd_uses_two_workers_and_no_control_socket():
    """Verify backend/Dockerfile CMD passes -w 2 and --no-control-socket."""
    dockerfile_text = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    cmd_match = re.search(r"^\s*CMD\s+(\[.*\])\s*$", dockerfile_text, re.MULTILINE)
    assert cmd_match is not None, "JSON-form CMD directive not found in backend/Dockerfile"

    cmd_args = json.loads(cmd_match.group(1))
    assert isinstance(cmd_args, list)
    assert _has_flag_pair(cmd_args, "-w", "2"), f"Dockerfile CMD must pass '-w 2': {cmd_args!r}"
    assert "--no-control-socket" in cmd_args, (
        f"Dockerfile CMD must include '--no-control-socket': {cmd_args!r}"
    )


def test_requirements_pins_gunicorn_minimum_version():
    """Verify backend/requirements.txt pins gunicorn>=25.1.0."""
    req_path = REPO_ROOT / "backend" / "requirements.txt"
    lines = [
        line.split("#", 1)[0].strip()
        for line in req_path.read_text(encoding="utf-8").splitlines()
    ]
    gunicorn_lines = [
        line for line in lines if re.match(r"^gunicorn(?:\[[^\]]+\])?(?:\s*[<>=!~].*)?$", line)
    ]
    assert gunicorn_lines, "gunicorn missing from backend/requirements.txt"

    spec = gunicorn_lines[0]
    match = re.search(r"(>=|==)\s*(\d+(?:\.\d+)*)", spec)
    assert match is not None, f"gunicorn must be pinned >=25.1.0, found: {spec!r}"

    version_tuple = tuple(int(part) for part in match.group(2).split("."))
    while len(version_tuple) < 3:
        version_tuple += (0,)
    assert version_tuple >= (25, 1, 0), f"gunicorn pin {spec!r} must be >= 25.1.0"


def test_nginx_prod_conf_worker_tuning():
    """Verify nginx.prod.conf sets worker_processes 1 and worker_connections 1024."""
    nginx_conf = (REPO_ROOT / "nginx.prod.conf").read_text(encoding="utf-8")
    assert re.search(r"^\s*worker_processes\s+1\s*;", nginx_conf, re.MULTILINE), (
        "nginx.prod.conf must set 'worker_processes 1;'"
    )
    assert re.search(r"^\s*worker_connections\s+1024\s*;", nginx_conf, re.MULTILINE), (
        "nginx.prod.conf must set 'worker_connections 1024;'"
    )


def test_env_example_documents_kafka_activity_topic():
    """Verify .env.example documents KAFKA_ACTIVITY_TOPIC=."""
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^KAFKA_ACTIVITY_TOPIC=", env_example, re.MULTILINE), (
        ".env.example must document KAFKA_ACTIVITY_TOPIC="
    )


def test_compose_all_services_define_memory_limits(compose_services: dict[str, dict[str, Any]]):
    """Verify all 18 services define deploy.resources.limits.memory with tuned caps."""
    assert len(compose_services) == 18, (
        f"Expected 18 services in docker-compose.prod.yml, found {len(compose_services)}"
    )
    assert set(compose_services) == set(EXPECTED_MEMORY_LIMITS)

    for name, expected_mem in EXPECTED_MEMORY_LIMITS.items():
        actual_mem = _service_memory_limit(compose_services[name])
        assert actual_mem is not None, f"Service {name!r} missing deploy.resources.limits.memory"
        assert actual_mem.upper() == expected_mem.upper(), (
            f"Service {name!r} memory limit {actual_mem!r} != expected {expected_mem!r}"
        )


def test_compose_clickhouse_mounts_low_mem_config(compose_services: dict[str, dict[str, Any]]):
    """Verify clickhouse mounts ./init-db/clickhouse-low-mem.xml read-only."""
    expected_mount = "./init-db/clickhouse-low-mem.xml:/etc/clickhouse-server/config.d/low_mem.xml:ro"
    mounts = _volume_mounts(compose_services["clickhouse"])
    assert expected_mount in mounts, (
        f"clickhouse service must mount {expected_mount!r}, got {mounts!r}"
    )


def test_compose_kafka_heap_and_thread_tuning(compose_services: dict[str, dict[str, Any]]):
    """Verify kafka service sets JVM heap cap and reduced broker/log settings."""
    env = _parse_env(compose_services["kafka"])
    heap_opts = env.get("KAFKA_HEAP_OPTS", "")
    assert "-Xmx256M" in heap_opts, f"KAFKA_HEAP_OPTS must include -Xmx256M, got {heap_opts!r}"

    expected_env = {
        "KAFKA_NUM_IO_THREADS": "2",
        "KAFKA_NUM_NETWORK_THREADS": "2",
        "KAFKA_BACKGROUND_THREADS": "2",
        "KAFKA_OFFSETS_TOPIC_NUM_PARTITIONS": "5",
        "KAFKA_LOG_RETENTION_HOURS": "24",
        "KAFKA_LOG_SEGMENT_BYTES": "67108864",
    }
    for key, expected_val in expected_env.items():
        assert env.get(key) == expected_val, (
            f"kafka env {key} must be {expected_val!r}, got {env.get(key)!r}"
        )


def test_compose_api_command_migrations_and_healthcheck(compose_services: dict[str, dict[str, Any]]):
    """Verify api uses -w 2, --no-control-socket, RUN_MIGRATIONS=1, and curl healthcheck."""
    api = compose_services["api"]
    tokens = _command_tokens(api)
    assert _has_flag_pair(tokens, "-w", "2"), f"api command must include '-w 2': {tokens!r}"
    assert "--no-control-socket" in tokens, (
        f"api command must include '--no-control-socket': {tokens!r}"
    )

    env = _parse_env(api)
    assert env.get("RUN_MIGRATIONS") == "1", (
        f"api must set RUN_MIGRATIONS=1, got {env.get('RUN_MIGRATIONS')!r}"
    )

    hc_cmd = _healthcheck_command(api)
    assert re.search(r"\bcurl\b", hc_cmd), f"api healthcheck must use curl: {hc_cmd!r}"
    assert not re.search(r"\bpython3?\s+-c\b", hc_cmd), (
        f"api healthcheck must not spawn python -c: {hc_cmd!r}"
    )


@pytest.mark.parametrize(
    "worker_name",
    ["consumer", "outbox-worker", "sync-checker", "scheduled-payments-worker"],
)
def test_compose_workers_skip_migrations_and_keep_healthchecks(
    compose_services: dict[str, dict[str, Any]],
    worker_name: str,
):
    """Verify worker services set RUN_MIGRATIONS=0 and retain valid healthchecks."""
    worker = compose_services[worker_name]
    env = _parse_env(worker)
    assert env.get("RUN_MIGRATIONS") == "0", (
        f"{worker_name} must set RUN_MIGRATIONS=0, got {env.get('RUN_MIGRATIONS')!r}"
    )

    hc = worker.get("healthcheck")
    assert isinstance(hc, dict) and hc.get("test") and not hc.get("disable", False), (
        f"{worker_name} must keep an active healthcheck block"
    )


def test_compose_postgres_services_tuned(compose_services: dict[str, dict[str, Any]]):
    """Verify all three Postgres services configure tuned shared_buffers and max_connections."""
    pg_tokens = _command_tokens(compose_services["postgres"])
    assert _has_pg_param(pg_tokens, "shared_buffers", "32MB"), (
        f"postgres command must set shared_buffers=32MB: {pg_tokens!r}"
    )
    assert _has_pg_param(pg_tokens, "max_connections", "60"), (
        f"postgres command must set max_connections=60: {pg_tokens!r}"
    )

    for db_name in ("vendor-simulator-db", "fed-gateway-db"):
        db_tokens = _command_tokens(compose_services[db_name])
        assert _has_pg_param(db_tokens, "shared_buffers", "16MB"), (
            f"{db_name} command must set shared_buffers=16MB: {db_tokens!r}"
        )
        assert _has_pg_param(db_tokens, "max_connections", "20"), (
            f"{db_name} command must set max_connections=20: {db_tokens!r}"
        )


def test_compose_frontend_proxy_and_autoheal_tuning(compose_services: dict[str, dict[str, Any]]):
    """Verify frontend NODE_OPTIONS, proxy healthcheck without nginx -t, and autoheal env vars."""
    frontend_env = _parse_env(compose_services["frontend"])
    node_opts = frontend_env.get("NODE_OPTIONS", "")
    assert "--max-old-space-size=192" in node_opts, (
        f"frontend NODE_OPTIONS must set --max-old-space-size=192, got {node_opts!r}"
    )

    proxy_hc = _healthcheck_command(compose_services["proxy"])
    assert proxy_hc, "proxy service must define a healthcheck command"
    assert "nginx -t" not in proxy_hc, (
        f"proxy healthcheck must not run 'nginx -t': {proxy_hc!r}"
    )

    autoheal_env = _parse_env(compose_services["autoheal"])
    expected_autoheal = {
        "AUTOHEAL_INTERVAL": "15",
        "AUTOHEAL_START_PERIOD": "60",
        "AUTOHEAL_DEFAULT_STOP_TIMEOUT": "20",
    }
    for key, expected_val in expected_autoheal.items():
        assert autoheal_env.get(key) == expected_val, (
            f"autoheal env {key} must be {expected_val!r}, got {autoheal_env.get(key)!r}"
        )


def test_compose_healthcheck_intervals_at_least_30s(compose_services: dict[str, dict[str, Any]]):
    """Verify every service healthcheck (skipping cloudflared and autoheal) has interval >= 30s."""
    for name, service in compose_services.items():
        if name in {"cloudflared", "autoheal"}:
            continue
        hc = service.get("healthcheck")
        assert isinstance(hc, dict), f"Service {name!r} missing healthcheck block"
        interval = hc.get("interval")
        assert interval is not None, f"Service {name!r} healthcheck missing interval"
        seconds = _parse_duration_seconds(interval)
        assert seconds >= 30.0, (
            f"Service {name!r} healthcheck interval {interval!r} ({seconds}s) must be >= 30s"
        )
