#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-unigraph-backend}"

echo "[DR] Listing pods in ${NAMESPACE}"
kubectl get pods -n "${NAMESPACE}"

echo "[DR] Deleting one pod to validate self-healing"
POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "${POD_NAME}" -n "${NAMESPACE}"

echo "[DR] Waiting for replacement pod"
kubectl wait --for=condition=Ready pods --all -n "${NAMESPACE}" --timeout=180s

echo "[DR] Failover smoke test complete"
