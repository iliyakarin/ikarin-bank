"""Tests for demo stack memory, thread, pool, and healthcheck resource tuning."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def compose_services() -> dict[str, dict]:
    return yaml.safe_load((REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8"))["services"]


def test_database_engine_pool_limits():
    import database

    assert database.engine.pool.size() == 5 and database.engine.pool._max_overflow == 5


def test_kafka_session_timeout_tuned():
    import constants
    import consumer

    consumer_src = (REPO_ROOT / "backend" / "consumer.py").read_text(encoding="utf-8")
    assert "from constants import OPTIMAL_SESSION_TIMEOUT" in consumer_src
    assert "OPTIMAL_SESSION_TIMEOUT =" not in consumer_src
    assert consumer.OPTIMAL_SESSION_TIMEOUT == constants.OPTIMAL_SESSION_TIMEOUT == 30000


def test_clickhouse_low_mem_xml():
    root = ET.parse(REPO_ROOT / "init-db" / "clickhouse-low-mem.xml").getroot()
    assert root.tag == "clickhouse"
    for tag in ("asynchronous_metric_log", "metric_log", "trace_log", "text_log",
                "part_log", "query_thread_log", "processors_profile_log"):
        elem = root.find(tag)
        assert elem is not None and elem.attrib.get("remove") == "1"
    caps = {"max_server_memory_usage": 536870912, "mark_cache_size": 67108864,
            "uncompressed_cache_size": 33554432, "background_schedule_pool_size": 16}
    for tag, cap in caps.items():
        elem = root.find(tag)
        assert elem is not None and elem.text and 0 < int(elem.text.strip()) <= cap
    bg_pool = int(root.findtext("background_pool_size"))
    for tag in ("number_of_free_entries_in_pool_to_lower_max_size_of_merge",
                "number_of_free_entries_in_pool_to_execute_mutation",
                "number_of_free_entries_in_pool_to_execute_optimize_entire_partition"):
        val = root.findtext(f"merge_tree/{tag}")
        assert val is not None and 0 < int(val.strip()) < bg_pool * 2


def test_entrypoint_gates_migrations():
    text = (REPO_ROOT / "backend" / "entrypoint.sh").read_text(encoding="utf-8")
    assert '${RUN_MIGRATIONS:-1}" = "1"' in text
    assert text.index("RUN_MIGRATIONS:-1") < text.index("alembic upgrade head")


def test_dockerfile_and_requirements():
    dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    cmd_match = re.search(r"^\s*CMD\s+(\[.*\])\s*$", dockerfile, re.MULTILINE)
    assert cmd_match is not None
    args = json.loads(cmd_match.group(1))
    assert args[args.index("-w") + 1] == "2" and "--no-control-socket" in args

    reqs = (REPO_ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8")
    req_match = re.search(r"^gunicorn\s*>=\s*(\d+(?:\.\d+)*)", reqs, re.MULTILINE)
    assert req_match is not None and tuple(int(p) for p in req_match.group(1).split(".")) >= (25, 1)


def test_nginx_and_env_example():
    nginx = (REPO_ROOT / "nginx.prod.conf").read_text(encoding="utf-8")
    assert re.search(r"^\s*worker_processes\s+1\s*;", nginx, re.MULTILINE)
    assert re.search(r"^\s*worker_connections\s+1024\s*;", nginx, re.MULTILINE)
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^KAFKA_ACTIVITY_TOPIC=", env_example, re.MULTILINE)


def test_compose_memory_budget(compose_services: dict[str, dict]):
    assert len(compose_services) == 18
    total_mib = 0
    for name, svc in compose_services.items():
        mem = str(svc["deploy"]["resources"]["limits"]["memory"]).strip()
        match = re.fullmatch(r"(\d+)([MG])", mem, re.IGNORECASE)
        assert match is not None, f"{name}: invalid memory limit {mem!r}"
        total_mib += int(match.group(1)) * (1024 if match.group(2).upper() == "G" else 1)
    assert total_mib <= 3840


def test_compose_clickhouse_and_kafka(compose_services: dict[str, dict]):
    ch_vols = compose_services["clickhouse"]["volumes"]
    assert "./init-db/clickhouse-low-mem.xml:/etc/clickhouse-server/config.d/low_mem.xml:ro" in ch_vols

    env = dict(item.split("=", 1) for item in compose_services["kafka"]["environment"])
    assert "-Xmx256M" in env["KAFKA_HEAP_OPTS"]
    caps = {
        "KAFKA_NUM_IO_THREADS": 2, "KAFKA_NUM_NETWORK_THREADS": 2, "KAFKA_BACKGROUND_THREADS": 2,
        "KAFKA_OFFSETS_TOPIC_NUM_PARTITIONS": 5, "KAFKA_LOG_RETENTION_HOURS": 24, "KAFKA_LOG_SEGMENT_BYTES": 67108864,
    }
    for key, cap in caps.items():
        assert 1 <= int(env[key]) <= cap


def test_compose_api_and_workers(compose_services: dict[str, dict]):
    api = compose_services["api"]
    tokens = api["command"].split() if isinstance(api["command"], str) else api["command"]
    assert tokens[tokens.index("-w") + 1] == "2" and "--no-control-socket" in tokens
    assert "RUN_MIGRATIONS=1" in api["environment"]
    hc_cmd = " ".join(api["healthcheck"]["test"])
    assert "curl" in hc_cmd and "python" not in hc_cmd

    for name in ("consumer", "outbox-worker", "sync-checker", "scheduled-payments-worker"):
        worker = compose_services[name]
        assert "RUN_MIGRATIONS=0" in worker["environment"]
        assert worker["healthcheck"].get("test") and not worker["healthcheck"].get("disable", False)


def test_compose_postgres_frontend_proxy_autoheal(compose_services: dict[str, dict]):
    for name, low, high in (("postgres", 55, 60), ("vendor-simulator-db", 10, 20), ("fed-gateway-db", 10, 20)):
        cmd = compose_services[name]["command"]
        assert "shared_buffers=" in cmd
        conn_match = re.search(r"max_connections=(\d+)", cmd)
        assert conn_match is not None and low <= int(conn_match.group(1)) <= high

    fe_env = dict(item.split("=", 1) for item in compose_services["frontend"]["environment"])
    assert "--max-old-space-size=192" in fe_env.get("NODE_OPTIONS", "")
    assert "nginx -t" not in " ".join(compose_services["proxy"]["healthcheck"]["test"])
    ah_env = dict(item.split("=", 1) for item in compose_services["autoheal"]["environment"])
    assert int(ah_env["AUTOHEAL_INTERVAL"]) >= 15


def test_compose_healthcheck_intervals(compose_services: dict[str, dict]):
    for name, svc in compose_services.items():
        if name in {"cloudflared", "autoheal"}:
            continue
        interval = str(svc["healthcheck"]["interval"]).strip()
        match = re.fullmatch(r"(\d+)([sm])", interval)
        assert match is not None and int(match.group(1)) * (60 if match.group(2) == "m" else 1) >= 30
