#!/bin/sh
set -eu

DEBEZIUM_CONNECT_URL="${DEBEZIUM_CONNECT_URL:-http://debezium-connect:8083}"
CONNECTOR_CONFIG_PATH="${CONNECTOR_CONFIG_PATH:-/config/connector-config.json}"

wait_for_connector_running() {
  connector_name="$1"
  retry=0

  while [ "${retry}" -lt 60 ]; do
    status_json="$(curl -fsS "${DEBEZIUM_CONNECT_URL}/connectors/${connector_name}/status" 2>/dev/null || true)"
    if [ -n "${status_json}" ]; then
      compact="$(echo "${status_json}" | tr -d '\n')"

      connector_failed=0
      if echo "${compact}" | grep -q '"connector":{[^}]*"state":"FAILED"'; then
        connector_failed=1
      fi

      task_failed=0
      if echo "${compact}" | grep -q '"tasks":\[[^]]*"state":"FAILED"'; then
        task_failed=1
      fi

      if [ "${connector_failed}" -eq 0 ] && [ "${task_failed}" -eq 0 ]; then
        task_total="$(echo "${compact}" | grep -o '"id":[0-9]\+' | wc -l | tr -d ' ')"
        running_count="$(echo "${compact}" | grep -o '"state":"RUNNING"' | wc -l | tr -d ' ')"
        expected_running=$((task_total + 1))

        if [ "${running_count}" -ge "${expected_running}" ]; then
          echo "[debezium-init] Connector ${connector_name} is RUNNING with ${task_total} task(s)"
          return 0
        fi
      fi
    fi

    retry=$((retry + 1))
    sleep 2
  done

  echo "[debezium-init] Connector ${connector_name} failed to reach RUNNING state"
  curl -fsS "${DEBEZIUM_CONNECT_URL}/connectors/${connector_name}/status" || true
  return 1
}

if [ ! -f "${CONNECTOR_CONFIG_PATH}" ]; then
  echo "[debezium-init] Missing connector config: ${CONNECTOR_CONFIG_PATH}"
  exit 1
fi

CONNECTOR_NAME="$(sed -n 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${CONNECTOR_CONFIG_PATH}" | head -n 1)"
if [ -z "${CONNECTOR_NAME}" ]; then
  echo "[debezium-init] Unable to parse connector name from ${CONNECTOR_CONFIG_PATH}"
  exit 1
fi

echo "[debezium-init] Waiting for Debezium Connect at ${DEBEZIUM_CONNECT_URL}..."
retry=0
until curl -fsS "${DEBEZIUM_CONNECT_URL}/connectors" >/dev/null 2>&1; do
  retry=$((retry + 1))
  if [ "${retry}" -ge 60 ]; then
    echo "[debezium-init] Debezium Connect did not become ready in time"
    exit 1
  fi
  sleep 2
done

if curl -fsS "${DEBEZIUM_CONNECT_URL}/connectors/${CONNECTOR_NAME}" >/dev/null 2>&1; then
  echo "[debezium-init] Connector ${CONNECTOR_NAME} already registered; verifying runtime state"
  wait_for_connector_running "${CONNECTOR_NAME}"
  exit 0
fi

status_code="$(curl -sS -o /tmp/debezium-register-response.json -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  --data @"${CONNECTOR_CONFIG_PATH}" \
  "${DEBEZIUM_CONNECT_URL}/connectors")"

case "${status_code}" in
  200|201|409)
    echo "[debezium-init] Connector ${CONNECTOR_NAME} registration finished with HTTP ${status_code}"
    ;;
  *)
    echo "[debezium-init] Connector registration failed with HTTP ${status_code}"
    cat /tmp/debezium-register-response.json || true
    exit 1
    ;;
esac

  wait_for_connector_running "${CONNECTOR_NAME}"
