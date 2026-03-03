#!/bin/bash
# ============================================================================
# Kafka entrypoint — renders JAAS config from .tpl template before startup.
# Substitutes __KAFKA_PASSWORD__ with the value of $KAFKA_PASSWORD env var.
# ============================================================================
set -euo pipefail

TPL_FILE="/etc/kafka/kafka_server_jaas.conf.tpl"
OUT_FILE="/etc/kafka/kafka_server_jaas.conf"

if [ -z "${KAFKA_PASSWORD:-}" ]; then
  echo "[ERROR] KAFKA_PASSWORD env var is not set. Cannot generate JAAS config." >&2
  exit 1
fi

echo "[kafka-entrypoint] Generating $OUT_FILE from template..."
sed "s|__KAFKA_PASSWORD__|${KAFKA_PASSWORD}|g" "$TPL_FILE" > "$OUT_FILE"
echo "[kafka-entrypoint] JAAS config written successfully."

# Hand off to the original Confluent entrypoint
exec /etc/confluent/docker/run
