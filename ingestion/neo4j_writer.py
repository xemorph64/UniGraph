from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sys
import time
import threading
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from confluent_kafka import Consumer, KafkaError

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.contracts.transaction_ingest_contract import (  # noqa: E402
    INGEST_CONTRACT_VERSION,
)
from backend.app.contracts.bridge_quality_gate import (  # noqa: E402
    build_bridge_quality_artifact,
    evaluate_dropped_invalid_policy,
)
from backend.app.contracts.transaction_ingest_payload import (  # noqa: E402
    normalize_bridge_ingest_payload,
)


@dataclass
class RuleSignal:
    txn_count: int = 0
    total_amount: float = 0.0
    updated_at: float = 0.0


class PipelineBridge:
    """
    Consume Flink outputs and bridge them into backend ingestion.

    Flow: Debezium -> Kafka(raw) -> Flink(enriched/rule) -> this bridge -> backend ML -> Neo4j -> LLM -> UI
    """

    def __init__(
        self,
        bootstrap_servers: str,
        enriched_topic: str,
        rule_topic: str,
        group_id: str,
        offset_reset: str,
        backend_url: str,
        trigger_llm: bool,
        llm_case_notes: str,
        signal_ttl_seconds: int,
        poll_timeout: float,
        max_messages: int,
        ingest_workers: int,
        max_inflight: int,
        ingest_batch_size: int,
        ingest_batch_wait_ms: int,
        enable_rule_reingest: bool,
        reingest_cooldown_seconds: float,
        http_timeout_seconds: float,
        log_level: str,
        stats_output_file: str | None,
        max_dropped_invalid: int,
        max_dropped_invalid_rate: float,
        dropped_invalid_rate_denominator: str,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.enriched_topic = enriched_topic
        self.rule_topic = rule_topic
        self.group_id = group_id
        self.offset_reset = offset_reset
        self.backend_url = backend_url.rstrip("/")
        self.trigger_llm = trigger_llm
        self.llm_case_notes = llm_case_notes
        self.signal_ttl_seconds = signal_ttl_seconds
        self.poll_timeout = poll_timeout
        self.max_messages = max_messages
        self.ingest_workers = max(1, ingest_workers)
        self.max_inflight = max(self.ingest_workers, max_inflight)
        self.ingest_batch_size = max(1, ingest_batch_size)
        self.ingest_batch_wait_seconds = max(0.0, ingest_batch_wait_ms / 1000.0)
        self.enable_rule_reingest = enable_rule_reingest
        self.reingest_cooldown_seconds = max(0.0, reingest_cooldown_seconds)
        self.http_timeout_seconds = max(1.0, http_timeout_seconds)
        self.log_level = log_level.upper()
        self.stats_output_file = (stats_output_file or "").strip()
        self.max_dropped_invalid = max_dropped_invalid
        self.max_dropped_invalid_rate = max_dropped_invalid_rate
        self.dropped_invalid_rate_denominator = dropped_invalid_rate_denominator

        self.running = True
        self.consumer: Consumer | None = None
        self.http = httpx.Client(
            timeout=self.http_timeout_seconds,
            limits=httpx.Limits(
                max_connections=max(200, self.ingest_workers * 8),
                max_keepalive_connections=max(100, self.ingest_workers * 4),
            ),
        )
        self.executor = ThreadPoolExecutor(
            max_workers=self.ingest_workers,
            thread_name_prefix="bridge-ingest",
        )
        self.inflight_ingest: set[Future] = set()

        self.rule_signals: dict[str, RuleSignal] = {}
        self.device_accounts: dict[str, set[str]] = defaultdict(set)
        self.txn_cache: dict[str, dict[str, Any]] = {}
        self.latest_txn_by_account: dict[str, str] = {}
        self.rule_reingest_last_sent: dict[str, float] = {}
        self.pending_batch: list[dict[str, Any]] = []
        self.pending_batch_since: float = 0.0
        self._stats_lock = threading.Lock()

        self.stats: dict[str, int] = {
            "messages_total": 0,
            "enriched_seen": 0,
            "rule_seen": 0,
            "dropped_invalid": 0,
            "ingested": 0,
            "alerts": 0,
            "llm_generated": 0,
            "errors": 0,
        }

    def _log(self, message: str, level: str = "INFO") -> None:
        levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        if levels.index(level) < levels.index(self.log_level):
            return
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        print(f"[{now}] [neo4j_writer] [{level}] {message}", flush=True)

    def _install_signal_handlers(self) -> None:
        def _stop_handler(signum: int, frame: Any) -> None:
            self.running = False
            self._log(f"Received signal {signum}. Stopping consumer loop.")

        signal.signal(signal.SIGINT, _stop_handler)
        signal.signal(signal.SIGTERM, _stop_handler)

    def _build_consumer(self) -> Consumer:
        return Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "auto.offset.reset": self.offset_reset,
                "enable.auto.commit": True,
            }
        )

    def _parse_json(self, payload: bytes | None) -> dict[str, Any] | None:
        if not payload:
            return None
        try:
            decoded = payload.decode("utf-8", errors="ignore")
            if not decoded.strip():
                return None
            data = json.loads(decoded)
            if isinstance(data, dict):
                return data
            return None
        except Exception:
            return None

    def _extract_raw_event(self, enriched_msg: dict[str, Any]) -> dict[str, Any] | None:
        event: Any = enriched_msg
        if "raw_event" in enriched_msg:
            event = enriched_msg.get("raw_event")
            if isinstance(event, str):
                try:
                    event = json.loads(event)
                except Exception:
                    return None

        if not isinstance(event, dict):
            return None

        # Handle possible Debezium wrappers if transform settings differ.
        if "payload" in event and isinstance(event["payload"], dict):
            event = event["payload"]
        if "after" in event and isinstance(event["after"], dict):
            event = event["after"]

        return event if isinstance(event, dict) else None

    def _coerce_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _coerce_int(self, value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(float(value))
        except Exception:
            return default

    def _active_signal_for(self, account_id: str) -> RuleSignal:
        signal_obj = self.rule_signals.get(account_id)
        if not signal_obj:
            return RuleSignal()
        if (time.time() - signal_obj.updated_at) > self.signal_ttl_seconds:
            return RuleSignal()
        return signal_obj

    def _inc_stat(self, key: str, delta: int = 1) -> None:
        with self._stats_lock:
            self.stats[key] = self.stats.get(key, 0) + delta

    def _process_completed_futures(self, block: bool = False) -> None:
        if not self.inflight_ingest:
            return

        if block:
            done, _ = wait(
                self.inflight_ingest,
                timeout=0.5,
                return_when=FIRST_COMPLETED,
            )
        else:
            done = {future for future in self.inflight_ingest if future.done()}

        if not done:
            return

        for future in done:
            self.inflight_ingest.discard(future)
            try:
                outcome = future.result()
            except Exception as ex:
                self._inc_stat("errors")
                self._log(f"Worker execution failed: {ex}", "WARN")
                continue

            if not outcome.get("ok"):
                error_delta = int(outcome.get("requested", 1)) if outcome.get("batch") else 1
                self._inc_stat("errors", error_delta)
                self._log(
                    f"Ingest failed txn={outcome.get('txn_id')} reason={outcome.get('reason')}: {outcome.get('error')}",
                    "WARN",
                )
                continue

            if outcome.get("batch"):
                ingested = int(outcome.get("ingested", 0))
                alerts_created = int(outcome.get("alerts_created", 0))
                self._inc_stat("ingested", ingested)
                if alerts_created > 0:
                    self._inc_stat("alerts", alerts_created)
                self._log(
                    f"BATCH INGEST reason={outcome.get('reason')} ingested={ingested}/{outcome.get('requested')} alerts={alerts_created}",
                    "DEBUG",
                )
                continue

            ingest_response = outcome.get("response") or {}
            txn_id = outcome.get("txn_id")
            account_id = outcome.get("account_id")
            self._inc_stat("ingested")

            if ingest_response.get("alert_id"):
                self._inc_stat("alerts")
                self._log(
                    f"ALERT txn={txn_id} account={account_id} risk={ingest_response.get('risk_score')} alert_id={ingest_response.get('alert_id')}",
                    "DEBUG",
                )
            else:
                self._log(
                    f"INGEST txn={txn_id} account={account_id} risk={ingest_response.get('risk_score')}",
                    "DEBUG",
                )

            if outcome.get("llm_generated"):
                self._inc_stat("llm_generated")

    def _ingest_worker(self, payload: dict[str, Any], reason: str) -> dict[str, Any]:
        txn_id = str(payload.get("txn_id") or "")
        account_id = str(payload.get("from_account") or "")
        try:
            ingest_response = self._post_ingest(payload)
            llm_generated = False
            if ingest_response:
                if self.trigger_llm and ingest_response.get("alert_id"):
                    self._trigger_llm_if_needed(ingest_response)
                    llm_generated = True
            return {
                "ok": True,
                "reason": reason,
                "txn_id": txn_id,
                "account_id": account_id,
                "response": ingest_response,
                "llm_generated": llm_generated,
            }
        except Exception as ex:
            return {
                "ok": False,
                "reason": reason,
                "txn_id": txn_id,
                "account_id": account_id,
                "error": str(ex),
            }

    def _ingest_batch_worker(self, payloads: list[dict[str, Any]], reason: str) -> dict[str, Any]:
        requested = len(payloads)
        try:
            ingest_response = self._post_ingest_batch(payloads)
            ingested = int(ingest_response.get("ingested") or requested)
            alerts_created = int(ingest_response.get("alerts_created") or 0)
            return {
                "ok": True,
                "batch": True,
                "reason": reason,
                "requested": requested,
                "ingested": ingested,
                "alerts_created": alerts_created,
            }
        except Exception as ex:
            return {
                "ok": False,
                "batch": True,
                "reason": reason,
                "requested": requested,
                "error": str(ex),
            }

    def _submit_pending_batch(self, reason: str) -> None:
        if not self.pending_batch:
            return

        while len(self.inflight_ingest) >= self.max_inflight:
            self._process_completed_futures(block=True)

        payloads = [dict(payload) for payload in self.pending_batch]
        self.pending_batch.clear()
        self.pending_batch_since = 0.0

        future = self.executor.submit(self._ingest_batch_worker, payloads, reason)
        self.inflight_ingest.add(future)

    def _maybe_flush_pending_batch_by_time(self) -> None:
        if self.ingest_batch_size <= 1:
            return
        if not self.pending_batch:
            return
        if self.ingest_batch_wait_seconds <= 0:
            return
        if self.pending_batch_since <= 0:
            return
        if (time.time() - self.pending_batch_since) >= self.ingest_batch_wait_seconds:
            self._submit_pending_batch(reason="time-flush")

    def _enqueue_ingest(self, payload: dict[str, Any], reason: str) -> None:
        if self.ingest_batch_size > 1:
            self.pending_batch.append(dict(payload))
            if self.pending_batch_since <= 0:
                self.pending_batch_since = time.time()
            if len(self.pending_batch) >= self.ingest_batch_size:
                self._submit_pending_batch(reason=f"{reason}-batch")
            return

        while len(self.inflight_ingest) >= self.max_inflight:
            self._process_completed_futures(block=True)

        future = self.executor.submit(self._ingest_worker, dict(payload), reason)
        self.inflight_ingest.add(future)

    def _build_ingest_payload(self, event: dict[str, Any]) -> dict[str, Any] | None:
        from_account = str(
            event.get("from_account")
            or event.get("account_id")
            or event.get("sender_account")
            or ""
        ).strip()
        to_account = str(event.get("to_account") or "UBI30100000000000").strip()
        txn_id = str(event.get("txn_id") or "").strip()

        if not from_account or not txn_id:
            return None

        amount = self._coerce_float(event.get("amount") or event.get("txn_amount"), 0.0)
        channel = str(event.get("channel") or "IMPS").strip().upper() or "IMPS"
        customer_id = str(event.get("customer_id") or f"CUST-{from_account}")
        description = str(event.get("description") or "CDC transaction")
        device_id = str(
            event.get("device_fingerprint")
            or event.get("device_id")
            or event.get("ip_address")
            or "DEV-UNKNOWN"
        )

        self.device_accounts[device_id].add(from_account)
        device_account_count = len(self.device_accounts[device_id])

        signal_obj = self._active_signal_for(from_account)
        velocity_1h = max(signal_obj.txn_count, 0)
        velocity_24h = max(signal_obj.txn_count * 2, velocity_1h)

        return {
            "contract_version": INGEST_CONTRACT_VERSION,
            "txn_id": txn_id,
            "from_account": from_account,
            "to_account": to_account,
            "amount": amount,
            "channel": channel,
            "customer_id": customer_id,
            "description": description,
            "device_id": device_id,
            "is_dormant": False,
            "device_account_count": max(1, device_account_count),
            "velocity_1h": velocity_1h,
            "velocity_24h": velocity_24h,
        }

    def _validate_ingest_payload(self, payload: dict[str, Any]) -> str | None:
        normalized, error = normalize_bridge_ingest_payload(payload)
        if error:
            return error

        if normalized is None:
            return "invalid ingest payload"

        payload.update(normalized)

        return None

    def _write_stats_artifact(self, exit_code: int, policy_failures: list[str]) -> bool:
        if not self.stats_output_file:
            return True

        artifact = build_bridge_quality_artifact(
            stats=self.stats,
            max_dropped_invalid=self.max_dropped_invalid,
            max_dropped_invalid_rate=self.max_dropped_invalid_rate,
            rate_denominator=self.dropped_invalid_rate_denominator,
            policy_failures=policy_failures,
            exit_code=exit_code,
        )

        output_path = Path(self.stats_output_file)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
            self._log(f"Wrote bridge stats artifact: {output_path}")
            return True
        except Exception as ex:
            self._log(f"Failed to write bridge stats artifact {output_path}: {ex}", "ERROR")
            return False

    def _upsert_rule_signal(self, rule_msg: dict[str, Any]) -> None:
        account_id = str(rule_msg.get("account_id") or "").strip()
        if not account_id:
            return

        txn_count = self._coerce_int(rule_msg.get("txn_count"), 0)
        total_amount = self._coerce_float(rule_msg.get("total_amount"), 0.0)
        is_flagged = bool(rule_msg.get("is_flagged", False))
        if rule_msg.get("rule") == "high_value_immediate":
            txn_count = max(txn_count, 5)
        if is_flagged:
            # Flink flagged this window, so push downstream velocity features into risk-triggering range.
            txn_count = max(txn_count, 5)
        if total_amount >= 1200000.0:
            txn_count = max(txn_count, 6)

        self.rule_signals[account_id] = RuleSignal(
            txn_count=max(txn_count, 0),
            total_amount=max(total_amount, 0.0),
            updated_at=time.time(),
        )

    def _post_ingest(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{self.backend_url}/transactions/ingest"
        resp = self.http.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None

    def _post_ingest_batch(self, payloads: list[dict[str, Any]]) -> dict[str, Any]:
        url = f"{self.backend_url}/transactions/ingest/batch"
        resp = self.http.post(url, json={"items": payloads})
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}

    def _trigger_llm_if_needed(self, ingest_response: dict[str, Any]) -> None:
        if not self.trigger_llm:
            return

        alert_id = ingest_response.get("alert_id")
        if not alert_id:
            return

        url = f"{self.backend_url}/reports/str/generate"
        payload = {"alert_id": alert_id, "case_notes": self.llm_case_notes}
        resp = self.http.post(url, json=payload)
        resp.raise_for_status()

    def _handle_enriched_message(self, message_data: dict[str, Any]) -> None:
        self._inc_stat("enriched_seen")

        raw_event = self._extract_raw_event(message_data)
        if not raw_event:
            self._log("Skipping enriched message: unable to parse raw_event", "DEBUG")
            return

        payload = self._build_ingest_payload(raw_event)
        if not payload:
            self._log("Skipping enriched message: required fields missing", "DEBUG")
            return

        payload_error = self._validate_ingest_payload(payload)
        if payload_error:
            self._inc_stat("dropped_invalid")
            self._log(
                f"Skipping enriched message: invalid ingest payload txn={payload.get('txn_id')} reason={payload_error}",
                "WARN",
            )
            return

        self.txn_cache[payload["txn_id"]] = payload
        self.latest_txn_by_account[payload["from_account"]] = payload["txn_id"]

        self._enqueue_ingest(payload, reason="enriched")

    def _handle_rule_message(self, message_data: dict[str, Any]) -> None:
        self._inc_stat("rule_seen")
        self._upsert_rule_signal(message_data)

        if not self.enable_rule_reingest:
            return

        account_id = str(message_data.get("account_id") or "").strip()
        txn_id = str(message_data.get("txn_id") or "").strip()

        if not txn_id and account_id:
            txn_id = self.latest_txn_by_account.get(account_id, "")

        # If we already observed the txn in enriched flow, re-score with latest rule signal.
        if txn_id and txn_id in self.txn_cache:
            if self.reingest_cooldown_seconds > 0:
                last_sent = self.rule_reingest_last_sent.get(txn_id, 0.0)
                if (time.time() - last_sent) < self.reingest_cooldown_seconds:
                    return

            payload = dict(self.txn_cache[txn_id])
            signal_obj = self._active_signal_for(account_id)
            payload["velocity_1h"] = max(payload.get("velocity_1h", 0), signal_obj.txn_count)
            payload["velocity_24h"] = max(payload.get("velocity_24h", 0), signal_obj.txn_count * 2)

            payload_error = self._validate_ingest_payload(payload)
            if payload_error:
                self._inc_stat("dropped_invalid")
                self._log(
                    f"Skipping rule reingest: invalid ingest payload txn={payload.get('txn_id')} reason={payload_error}",
                    "WARN",
                )
                return

            self.rule_reingest_last_sent[txn_id] = time.time()
            self._enqueue_ingest(payload, reason="rule")

    def run(self) -> int:
        exit_code = 0
        self._install_signal_handlers()
        self.consumer = self._build_consumer()
        self.consumer.subscribe([self.enriched_topic, self.rule_topic])

        self._log(
            f"Subscribed to topics={self.enriched_topic},{self.rule_topic} "
            f"bootstrap={self.bootstrap_servers} backend={self.backend_url} trigger_llm={self.trigger_llm} "
            f"workers={self.ingest_workers} max_inflight={self.max_inflight} "
            f"batch_size={self.ingest_batch_size} batch_wait_ms={int(self.ingest_batch_wait_seconds * 1000)} "
            f"rule_reingest={self.enable_rule_reingest}"
        )
        if self.trigger_llm and self.ingest_batch_size > 1:
            self._log(
                "LLM report generation is disabled in batch mode because batch ingest does not return alert IDs.",
                "WARN",
            )

        try:
            while self.running:
                self._process_completed_futures(block=False)
                self._maybe_flush_pending_batch_by_time()
                msg = self.consumer.poll(self.poll_timeout)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    self._inc_stat("errors")
                    self._log(f"Kafka error: {msg.error()}", "WARN")
                    continue

                self._inc_stat("messages_total")
                data = self._parse_json(msg.value())
                if not data:
                    continue

                topic = msg.topic()
                try:
                    if topic == self.enriched_topic:
                        self._handle_enriched_message(data)
                    elif topic == self.rule_topic:
                        self._handle_rule_message(data)
                except Exception as ex:
                    self._inc_stat("errors")
                    self._log(f"Processing error topic={topic}: {ex}", "WARN")

                if self.max_messages > 0 and self.stats["messages_total"] >= self.max_messages:
                    self._log(f"Reached max-messages={self.max_messages}. Stopping.")
                    break

        finally:
            if self.consumer is not None:
                self.consumer.close()

            if self.pending_batch:
                self._submit_pending_batch(reason="shutdown-flush")

            while self.inflight_ingest:
                self._process_completed_futures(block=True)

            self.executor.shutdown(wait=True)
            self.http.close()
            policy_failures, drop_rate, dropped_invalid, denominator = evaluate_dropped_invalid_policy(
                self.stats,
                max_dropped_invalid=self.max_dropped_invalid,
                max_dropped_invalid_rate=self.max_dropped_invalid_rate,
                rate_denominator=self.dropped_invalid_rate_denominator,
            )
            if self.max_dropped_invalid >= 0 or self.max_dropped_invalid_rate >= 0:
                self._log(
                    "Quality gate observed "
                    f"dropped_invalid={dropped_invalid} denominator={denominator} "
                    f"drop_rate={drop_rate:.6f}",
                    "INFO",
                )

            for failure in policy_failures:
                self._log(f"Quality gate failure: {failure}", "ERROR")

            exit_code = 0 if self.stats["errors"] == 0 and not policy_failures else 1
            if not self._write_stats_artifact(exit_code, policy_failures):
                exit_code = 1
            self._log(f"Summary: {json.dumps(self.stats)}")

        return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Bridge Flink Kafka streams into UniGRAPH backend/Neo4j/LLM pipeline")
    parser.add_argument("--bootstrap-servers", default="localhost:19092")
    parser.add_argument("--enriched-topic", default="enriched-transactions")
    parser.add_argument("--rule-topic", default="rule-violations")
    parser.add_argument("--group-id", default="unigraph-neo4j-writer")
    parser.add_argument("--offset-reset", default="latest", choices=["latest", "earliest"])
    parser.add_argument("--backend-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--trigger-llm", action="store_true")
    parser.add_argument("--llm-case-notes", default="Auto-generated from CDC streaming pipeline")
    parser.add_argument("--signal-ttl-seconds", type=int, default=240)
    parser.add_argument("--poll-timeout", type=float, default=1.0)
    parser.add_argument("--max-messages", type=int, default=0)
    parser.add_argument("--ingest-workers", type=int, default=64)
    parser.add_argument("--max-inflight", type=int, default=4000)
    parser.add_argument("--ingest-batch-size", type=int, default=1)
    parser.add_argument("--ingest-batch-wait-ms", type=int, default=25)
    parser.add_argument("--disable-rule-reingest", action="store_true")
    parser.add_argument("--reingest-cooldown-seconds", type=float, default=5.0)
    parser.add_argument("--http-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARN", "ERROR"])
    parser.add_argument("--stats-output-file", default="")
    parser.add_argument("--max-dropped-invalid", type=int, default=-1)
    parser.add_argument("--max-dropped-invalid-rate", type=float, default=-1.0)
    parser.add_argument(
        "--dropped-invalid-rate-denominator",
        default="enriched_seen",
        choices=["enriched_seen", "messages_total"],
    )
    args = parser.parse_args()

    if args.max_dropped_invalid < -1:
        raise SystemExit("--max-dropped-invalid must be >= -1")
    if args.max_dropped_invalid_rate < -1.0:
        raise SystemExit("--max-dropped-invalid-rate must be >= -1")

    bridge = PipelineBridge(
        bootstrap_servers=args.bootstrap_servers,
        enriched_topic=args.enriched_topic,
        rule_topic=args.rule_topic,
        group_id=args.group_id,
        offset_reset=args.offset_reset,
        backend_url=args.backend_url,
        trigger_llm=args.trigger_llm,
        llm_case_notes=args.llm_case_notes,
        signal_ttl_seconds=args.signal_ttl_seconds,
        poll_timeout=args.poll_timeout,
        max_messages=args.max_messages,
        ingest_workers=args.ingest_workers,
        max_inflight=args.max_inflight,
        ingest_batch_size=args.ingest_batch_size,
        ingest_batch_wait_ms=args.ingest_batch_wait_ms,
        enable_rule_reingest=not args.disable_rule_reingest,
        reingest_cooldown_seconds=args.reingest_cooldown_seconds,
        http_timeout_seconds=args.http_timeout_seconds,
        log_level=args.log_level,
        stats_output_file=args.stats_output_file,
        max_dropped_invalid=args.max_dropped_invalid,
        max_dropped_invalid_rate=args.max_dropped_invalid_rate,
        dropped_invalid_rate_denominator=args.dropped_invalid_rate_denominator,
    )
    raise SystemExit(bridge.run())


if __name__ == "__main__":
    main()
