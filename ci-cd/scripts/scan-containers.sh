#!/usr/bin/env bash
set -euo pipefail
trivy fs --severity CRITICAL,HIGH --exit-code 1 .
