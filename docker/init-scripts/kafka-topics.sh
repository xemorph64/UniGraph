#!/bin/bash
set -euo pipefail

KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP:-kafka-1:9092}"

echo "[kafka-init] Waiting for Kafka broker at ${KAFKA_BOOTSTRAP}..."
until kafka-broker-api-versions --bootstrap-server "${KAFKA_BOOTSTRAP}" >/dev/null 2>&1; do
  sleep 2
done

create_or_update_topic() {
  local topic="$1"
  local partitions="$2"
  local replication_factor="$3"
  local retention_ms="$4"
  local min_isr="$5"

  kafka-topics --create --if-not-exists \
    --bootstrap-server "${KAFKA_BOOTSTRAP}" \
    --topic "${topic}" \
    --partitions "${partitions}" \
    --replication-factor "${replication_factor}" \
    --config "retention.ms=${retention_ms}" \
    --config "min.insync.replicas=${min_isr}" >/dev/null

  # Ensure critical durability settings are applied even if the topic already existed.
  kafka-configs --bootstrap-server "${KAFKA_BOOTSTRAP}" \
    --entity-type topics \
    --entity-name "${topic}" \
    --alter \
    --add-config "retention.ms=${retention_ms},min.insync.replicas=${min_isr}" >/dev/null
}

create_or_update_topic raw-transactions 12 3 604800000 1
create_or_update_topic enriched-transactions 12 3 604800000 1
create_or_update_topic rule-violations 6 3 259200000 1
create_or_update_topic ml-scores 12 3 259200000 1
create_or_update_topic alerts 6 3 604800000 1
create_or_update_topic training-queue 3 3 2592000000 1

# Debezium heartbeats use a dedicated topic; RF=1 with min.insync.replicas=1 avoids local-cluster ISR deadlocks.
create_or_update_topic __debezium-heartbeat.cbs 1 1 604800000 1

echo "[kafka-init] Kafka topics are ready."