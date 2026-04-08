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
