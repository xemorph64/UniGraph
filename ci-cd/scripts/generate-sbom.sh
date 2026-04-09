#!/usr/bin/env bash
set -euo pipefail
syft . -o cyclonedx-json > sbom.cdx.json
