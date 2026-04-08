#!/bin/bash
KAFKA_BOOTSTRAP=kafka-1:9092

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic raw-transactions \
  --partitions 12 --replication-factor 3 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic enriched-transactions \
  --partitions 12 --replication-factor 3 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic rule-violations \
  --partitions 6 --replication-factor 3 \
  --config retention.ms=259200000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic ml-scores \
  --partitions 12 --replication-factor 3 \
  --config retention.ms=259200000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic alerts \
  --partitions 6 --replication-factor 3 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic training-queue \
  --partitions 3 --replication-factor 3 \
  --config retention.ms=2592000000

# Debezium heartbeats use a dedicated topic; RF=1 with min.insync.replicas=1 avoids local-cluster ISR deadlocks.
kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic __debezium-heartbeat.cbs \
  --partitions 1 --replication-factor 1 \
  --config min.insync.replicas=1 \
  --config retention.ms=604800000