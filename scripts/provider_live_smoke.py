from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return value[:2] + "***" + value[-2:]


def _tcp_check(url: str, timeout: float) -> tuple[bool, str]:
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        return False, f"invalid URL: {url}"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"tcp reachable {host}:{port}"
    except OSError as ex:
        return False, f"tcp unreachable {host}:{port} ({ex})"


def _finacle_auth_check(timeout: float) -> dict:
    base_url = os.getenv("FINACLE_API_URL", "").strip().rstrip("/")
    client_id = os.getenv("FINACLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("FINACLE_CLIENT_SECRET", "").strip()

    if not base_url:
        return {"target": "finacle", "skipped": True, "reason": "FINACLE_API_URL missing"}

    ok, msg = _tcp_check(base_url, timeout)
    if not ok:
        return {"target": "finacle", "ok": False, "detail": msg}

    if not client_id or not client_secret:
        return {
            "target": "finacle",
            "ok": False,
            "detail": "FINACLE_CLIENT_ID/FINACLE_CLIENT_SECRET missing",
            "client_id_hint": _mask(client_id),
        }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{base_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
        body = {}
        try:
            body = response.json()
        except Exception:
            body = {"text": response.text[:200]}

        token_present = isinstance(body, dict) and bool(body.get("access_token"))
        return {
            "target": "finacle",
            "ok": response.status_code == 200 and token_present,
            "status_code": response.status_code,
            "token_received": token_present,
        }
    except Exception as ex:
        return {"target": "finacle", "ok": False, "detail": str(ex)}


def _fiu_connectivity_check(timeout: float) -> dict:
    base_url = os.getenv("FIU_IND_API_URL", "").strip().rstrip("/")
    cert_path = os.getenv("FIU_IND_MTLS_CERT_PATH", "").strip()
    key_path = os.getenv("FIU_IND_MTLS_KEY_PATH", "").strip()
    reference_id = os.getenv("FIU_REFERENCE_ID", "").strip()

    if not base_url:
        return {"target": "fiu_ind", "skipped": True, "reason": "FIU_IND_API_URL missing"}

    ok, msg = _tcp_check(base_url, timeout)
    if not ok:
        return {"target": "fiu_ind", "ok": False, "detail": msg}

    if not cert_path or not key_path:
        return {
            "target": "fiu_ind",
            "ok": False,
            "detail": "FIU_IND_MTLS_CERT_PATH/FIU_IND_MTLS_KEY_PATH missing",
        }

    cert_file = Path(cert_path)
    key_file = Path(key_path)
    if not cert_file.exists() or not key_file.exists():
        return {
            "target": "fiu_ind",
            "ok": False,
            "detail": "mTLS cert/key file not found",
            "cert_exists": cert_file.exists(),
            "key_exists": key_file.exists(),
        }

    if not reference_id:
        return {
            "target": "fiu_ind",
            "ok": True,
            "detail": "tcp + mTLS file checks passed (FIU_REFERENCE_ID not set; status API not called)",
        }

    try:
        with httpx.Client(timeout=timeout, cert=(cert_path, key_path)) as client:
            response = client.get(f"{base_url}/v2/submissions/{reference_id}/status")
        return {
            "target": "fiu_ind",
            "ok": response.status_code in {200, 202, 401, 403, 404},
            "status_code": response.status_code,
        }
    except Exception as ex:
        return {"target": "fiu_ind", "ok": False, "detail": str(ex)}


def _ncrp_connectivity_check(timeout: float) -> dict:
    base_url = os.getenv("NCRP_API_URL", "").strip().rstrip("/")
    api_key = os.getenv("NCRP_API_KEY", "").strip()
    health_url = os.getenv("NCRP_HEALTH_URL", "").strip()

    if not base_url:
        return {"target": "ncrp", "skipped": True, "reason": "NCRP_API_URL missing"}

    ok, msg = _tcp_check(base_url, timeout)
    if not ok:
        return {"target": "ncrp", "ok": False, "detail": msg}

    url = health_url or f"{base_url}/api/v1/health"
    headers = {"X-API-Key": api_key} if api_key else {}

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers)
        return {
            "target": "ncrp",
            "ok": response.status_code < 500,
            "status_code": response.status_code,
        }
    except Exception as ex:
        return {"target": "ncrp", "ok": False, "detail": str(ex)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate live provider connectivity/auth for Finacle, FIU-IND, and NCRP"
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    checks = [
        _finacle_auth_check(args.timeout),
        _fiu_connectivity_check(args.timeout),
        _ncrp_connectivity_check(args.timeout),
    ]

    failures = [c for c in checks if not c.get("ok", False) and not c.get("skipped")]
    result = {
        "status": "PASS" if not failures else "FAIL",
        "checks": checks,
    }

    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
