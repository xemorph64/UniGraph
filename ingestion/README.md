# Ingestion Layer

This folder contains the data ingestion pipeline components:

- Debezium mock producer for raw transaction events
- Flink enrichment job (raw-transactions -> enriched-transactions)
- Flink anomaly job (enriched-transactions -> rule-violations)

## 1) Validate Mock Producer

Run unit tests:

```powershell
& "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe" -m unittest ingestion/debezium/tests/test_mock_cbs_generator.py -v
```

Generate sample events to a JSONL file:

```powershell
& "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe" ingestion/debezium/mock-cbs-generator.py --scenario mixed --count 200 --output ingestion/debezium/mock-events.jsonl
```

Publish events to Kafka:

```powershell
& "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe" ingestion/debezium/mock-cbs-generator.py --scenario mixed --count 200 --publish --bootstrap-servers localhost:19092
```

## 2) Build Flink Jobs

Prerequisites:

- JDK 11+
- Maven 3.9+

Build shaded jobs jar:

```powershell
mvn -f ingestion/flink/pom.xml -DskipTests package
```

Output jar:

- ingestion/flink/target/unigraph-ingestion-jobs.jar

## 3) Submit Flink Jobs

With Flink JobManager running on localhost:8082:

```powershell
powershell -ExecutionPolicy Bypass -File ingestion/flink/submit-jobs.ps1
```

Optional arguments:

```powershell
powershell -ExecutionPolicy Bypass -File ingestion/flink/submit-jobs.ps1 -JobManagerUrl http://localhost:8082 -JarPath ingestion/flink/target/unigraph-ingestion-jobs.jar
```

## Data Flow

- raw-transactions: source transaction events (mock/debezium)
- enriched-transactions: enrichment output
- rule-violations: windowed velocity anomalies

## 4) High-Throughput Bridge Mode

Run the Kafka-to-backend bridge with concurrent ingest workers:

```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python ingestion/neo4j_writer.py \
	--bootstrap-servers localhost:19092 \
	--backend-url http://localhost:8000/api/v1 \
	--ingest-workers 128 \
	--max-inflight 8000 \
	--ingest-batch-size 200 \
	--ingest-batch-wait-ms 20 \
	--disable-rule-reingest \
	--http-timeout-seconds 8
```

Notes:

- `--ingest-workers`: number of concurrent backend POST workers.
- `--max-inflight`: bounded queue for backpressure.
- `--ingest-batch-size`: send queued records to `/transactions/ingest/batch` in chunks for much higher throughput.
- `--ingest-batch-wait-ms`: max wait before flushing a partial batch.
- `--disable-rule-reingest`: avoids duplicate backend reingest on rule topic for max throughput.
- `--reingest-cooldown-seconds`: throttle rule-triggered reingest if reingest is enabled.

## 5) Throughput Benchmarks

Stream benchmark (Kafka -> Flink):

```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python ingestion/benchmark_ingestion.py --bootstrap localhost:19092 --count 10000 --timeout 240 --profile optimized
```

Backend ingest benchmark (HTTP ingest API):

```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python scripts/benchmark_backend_ingest.py --url http://localhost:8000/api/v1/transactions/ingest --count 10000 --concurrency 256 --timeout 8
/home/ojasbhalerao/Documents/Uni/.venv/bin/python scripts/benchmark_backend_ingest.py --url http://localhost:8000/api/v1/transactions/ingest/batch --count 20000 --batch-size 200 --concurrency 32 --timeout 8
```

## 6) Strict Replay Quality Gate

For release-validation replay runs, fail fast if malformed payload drops exceed policy.

Run bridge with stats artifact + thresholds:

```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python ingestion/neo4j_writer.py \
	--bootstrap-servers localhost:19092 \
	--backend-url http://localhost:8000/api/v1 \
	--max-messages 2000 \
	--stats-output-file ingestion/strict-replay-bridge-stats.json \
	--max-dropped-invalid 0 \
	--max-dropped-invalid-rate 0.0 \
	--dropped-invalid-rate-denominator enriched_seen
```

Verify artifact explicitly (can be run in CI or post-run checks):

```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python scripts/verify_strict_replay_artifact.py \
	--stats-file ingestion/strict-replay-bridge-stats.json \
	--max-dropped-invalid 0 \
	--max-dropped-invalid-rate 0.0 \
	--dropped-invalid-rate-denominator enriched_seen
```

Threshold notes:

- Use `0` / `0.0` for fail-closed strict validation.
- Use `-1` to disable an individual threshold.
