#!/bin/bash
set -e

usage() {
  echo "Usage: $0 host:port [--timeout seconds] [-- command args]"
  exit 1
}

if [ $# -lt 1 ]; then
  usage
fi

HOST_PORT="$1"
shift
HOST="${HOST_PORT%:*}"
PORT="${HOST_PORT#*:}"
TIMEOUT=30

if [ -z "$HOST" ] || [ -z "$PORT" ] || [ "$HOST" = "$PORT" ]; then
  usage
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --timeout|-t)
      TIMEOUT="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      usage
      ;;
  esac
done

START_TIME="$(date +%s)"

while ! (echo > "/dev/tcp/$HOST/$PORT") >/dev/null 2>&1; do
  NOW="$(date +%s)"
  ELAPSED=$((NOW - START_TIME))
  if [ "$TIMEOUT" -gt 0 ] && [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "Timed out waiting for $HOST:$PORT"
    exit 1
  fi
  sleep 1
done

if [ $# -gt 0 ]; then
  exec "$@"
fi
