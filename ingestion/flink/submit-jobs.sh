#!/usr/bin/env bash
set -euo pipefail

JOB_MANAGER_URL="${1:-http://localhost:8082}"
JAR_PATH="${2:-ingestion/flink/target/unigraph-ingestion-jobs.jar}"

if [[ ! -f "${JAR_PATH}" ]]; then
  echo "[flink-submit] Jar not found at ${JAR_PATH}. Building with Maven..."
  mvn -f ingestion/flink/pom.xml -DskipTests package
fi

echo "[flink-submit] Uploading jar to ${JOB_MANAGER_URL}"
UPLOAD_RESPONSE="$(curl -sS -X POST -H 'Expect:' -F "jarfile=@${JAR_PATH}" "${JOB_MANAGER_URL}/jars/upload")"
JAR_ID="$(echo "${UPLOAD_RESPONSE}" | sed -n 's|.*"filename":".*/\([^"]*\)".*|\1|p')"

if [[ -z "${JAR_ID}" ]]; then
  echo "[flink-submit] Unexpected upload response: ${UPLOAD_RESPONSE}"
  exit 1
fi

echo "[flink-submit] Uploaded jar id: ${JAR_ID}"

submit_job() {
  local entry_class="$1"
  local payload
  payload="{\"entryClass\":\"${entry_class}\"}"
  local response
  response="$(curl -sS -X POST -H 'Content-Type: application/json' -d "${payload}" "${JOB_MANAGER_URL}/jars/${JAR_ID}/run")"
  echo "[flink-submit] Submitted ${entry_class}: ${response}"
}

submit_job "TransactionEnrichmentJob"
submit_job "AnomalyWindowJob"

echo "[flink-submit] Flink jobs submitted."
