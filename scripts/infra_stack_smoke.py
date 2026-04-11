from __future__ import annotations

import argparse
import json
import socket
import subprocess
from typing import Iterable

import httpx


def _run(command: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(command, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _socket_ok(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"reachable {host}:{port}"
    except OSError as ex:
        return False, f"unreachable {host}:{port} ({ex})"


def _http_ok(url: str, timeout: float) -> tuple[bool, int | None, str]:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
        if response.status_code < 500:
            return True, response.status_code, "ok"
        return False, response.status_code, f"server status {response.status_code}"
    except Exception as ex:
        return False, None, str(ex)


def _compose_services_up(compose_file: str, expected: Iterable[str]) -> dict:
    code, out, err = _run(["docker", "compose", "-f", compose_file, "ps"])
    if code != 0:
        return {
            "ok": False,
            "detail": f"docker compose ps failed: {(err or out).strip()}",
        }

    missing = []
    unhealthy = []
    text = out.lower()
    for svc in expected:
        if svc.lower() not in text:
            missing.append(svc)
            continue
        # We accept "Up" and "running" state text from compose versions.
        svc_line = ""
        for line in out.splitlines():
            if svc in line:
                svc_line = line
                break
        svc_line_l = svc_line.lower()
        if "up" not in svc_line_l and "running" not in svc_line_l:
            unhealthy.append({"service": svc, "line": svc_line.strip()})

    return {
        "ok": not missing and not unhealthy,
        "missing": missing,
        "unhealthy": unhealthy,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke-check infra stack readiness (docker compose + service probes)"
    )
    parser.add_argument("--compose-file", default="docker/docker-compose.yml")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--backend-health-url", default="")
    args = parser.parse_args()

    expected_services = [
        "kafka-1",
        "schema-registry",
        "debezium-connect",
        "neo4j",
        "cassandra",
        "redis",
        "vault",
    ]

    checks: list[dict] = []

    compose_state = _compose_services_up(args.compose_file, expected_services)
    checks.append({"target": "docker_compose", **compose_state})

    for host, port, name in [
        ("localhost", 19092, "kafka_bootstrap"),
        ("localhost", 8081, "schema_registry"),
        ("localhost", 8083, "debezium_connect"),
        ("localhost", 7474, "neo4j_http"),
        ("localhost", 7687, "neo4j_bolt"),
        ("localhost", 9042, "cassandra_cql"),
        ("localhost", 6379, "redis"),
        ("localhost", 8200, "vault"),
    ]:
        ok, detail = _socket_ok(host, port, args.timeout)
        checks.append({"target": name, "ok": ok, "detail": detail})

    for url, name in [
        ("http://localhost:8081/subjects", "schema_registry_http"),
        ("http://localhost:8083/connectors", "debezium_http"),
        ("http://localhost:8082/overview", "flink_jobmanager_http"),
        ("http://localhost:8200/v1/sys/health", "vault_http"),
    ]:
        ok, status, detail = _http_ok(url, args.timeout)
        checks.append(
            {
                "target": name,
                "ok": ok,
                "status_code": status,
                "detail": detail,
            }
        )

    if args.backend_health_url:
        ok, status, detail = _http_ok(args.backend_health_url, args.timeout)
        checks.append(
            {
                "target": "backend_health",
                "ok": ok,
                "status_code": status,
                "detail": detail,
            }
        )

    failures = [c for c in checks if not c.get("ok", False)]
    result = {
        "status": "PASS" if not failures else "FAIL",
        "checks": checks,
    }

    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
