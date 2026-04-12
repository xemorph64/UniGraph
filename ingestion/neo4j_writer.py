from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from confluent_kafka import Consumer, KafkaError


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
        log_level: str,
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
        self.log_level = log_level.upper()

        self.running = True
        self.consumer: Consumer | None = None
        self.http = httpx.Client(timeout=20.0)

        self.rule_signals: dict[str, RuleSignal] = {}
        self.device_accounts: dict[str, set[str]] = defaultdict(set)
        self.txn_cache: dict[str, dict[str, Any]] = {}
        self.latest_txn_by_account: dict[str, str] = {}

        self.stats: dict[str, int] = {
            "messages_total": 0,
            "enriched_seen": 0,
            "rule_seen": 0,
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

    def _build_ingest_payload(self, event: dict[str, Any]) -> dict[str, Any] | None:
        from_account = str(event.get("from_account") or event.get("account_id") or "").strip()
        to_account = str(event.get("to_account") or "UBI30100000000000").strip()
        txn_id = str(event.get("txn_id") or "").strip()

        if not from_account or not txn_id:
            return None

        amount = self._coerce_float(event.get("amount") or event.get("txn_amount"), 0.0)
        channel = str(event.get("channel") or "IMPS").strip() or "IMPS"
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
        self.stats["llm_generated"] += 1

    def _handle_enriched_message(self, message_data: dict[str, Any]) -> None:
        self.stats["enriched_seen"] += 1

        raw_event = self._extract_raw_event(message_data)
        if not raw_event:
            self._log("Skipping enriched message: unable to parse raw_event", "DEBUG")
            return

        payload = self._build_ingest_payload(raw_event)
        if not payload:
            self._log("Skipping enriched message: required fields missing", "DEBUG")
            return

        self.txn_cache[payload["txn_id"]] = payload
        self.latest_txn_by_account[payload["from_account"]] = payload["txn_id"]

        ingest_response = self._post_ingest(payload)
        if not ingest_response:
            return

        self.stats["ingested"] += 1
        if ingest_response.get("alert_id"):
            self.stats["alerts"] += 1

        self._trigger_llm_if_needed(ingest_response)

        if ingest_response.get("alert_id"):
            self._log(
                f"ALERT txn={payload['txn_id']} account={payload['from_account']} "
                f"risk={ingest_response.get('risk_score')} alert_id={ingest_response.get('alert_id')}"
            )
        else:
            self._log(
                f"INGEST txn={payload['txn_id']} account={payload['from_account']} "
                f"risk={ingest_response.get('risk_score')}",
                "DEBUG",
            )

    def _handle_rule_message(self, message_data: dict[str, Any]) -> None:
        self.stats["rule_seen"] += 1
        self._upsert_rule_signal(message_data)

        account_id = str(message_data.get("account_id") or "").strip()
        txn_id = str(message_data.get("txn_id") or "").strip()

        if not txn_id and account_id:
            txn_id = self.latest_txn_by_account.get(account_id, "")

        # If we already observed the txn in enriched flow, re-score with latest rule signal.
        if txn_id and txn_id in self.txn_cache:
            payload = dict(self.txn_cache[txn_id])
            signal_obj = self._active_signal_for(account_id)
            payload["velocity_1h"] = max(payload.get("velocity_1h", 0), signal_obj.txn_count)
            payload["velocity_24h"] = max(payload.get("velocity_24h", 0), signal_obj.txn_count * 2)
            try:
                ingest_response = self._post_ingest(payload)
                if ingest_response:
                    self.stats["ingested"] += 1
                    if ingest_response.get("alert_id"):
                        self.stats["alerts"] += 1
                        self._trigger_llm_if_needed(ingest_response)
            except Exception as ex:
                self.stats["errors"] += 1
                self._log(f"Failed rule-driven reingest txn={txn_id}: {ex}", "WARN")

    def run(self) -> int:
        self._install_signal_handlers()
        self.consumer = self._build_consumer()
        self.consumer.subscribe([self.enriched_topic, self.rule_topic])

        self._log(
            f"Subscribed to topics={self.enriched_topic},{self.rule_topic} "
            f"bootstrap={self.bootstrap_servers} backend={self.backend_url} trigger_llm={self.trigger_llm}"
        )

        try:
            while self.running:
                msg = self.consumer.poll(self.poll_timeout)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    self.stats["errors"] += 1
                    self._log(f"Kafka error: {msg.error()}", "WARN")
                    continue

                self.stats["messages_total"] += 1
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
                    self.stats["errors"] += 1
                    self._log(f"Processing error topic={topic}: {ex}", "WARN")

                if self.max_messages > 0 and self.stats["messages_total"] >= self.max_messages:
                    self._log(f"Reached max-messages={self.max_messages}. Stopping.")
                    break

        finally:
            if self.consumer is not None:
                self.consumer.close()
            self.http.close()
            self._log(f"Summary: {json.dumps(self.stats)}")

        return 0 if self.stats["errors"] == 0 else 1


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
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARN", "ERROR"])
    args = parser.parse_args()

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
        log_level=args.log_level,
    )
    raise SystemExit(bridge.run())


if __name__ == "__main__":
    main()
