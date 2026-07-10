#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${GPU_RUNTIME_DIR:-$ROOT_DIR/.runtime/gpu-inference}"
PID_FILE="$RUNTIME_DIR/service.pid"
PORT_FILE="$RUNTIME_DIR/service.port"
LOG_FILE="$RUNTIME_DIR/service.log"
LOCK_FILE="$RUNTIME_DIR/service.lock"
ENV_FILE="${GPU_ENV_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/medicine-gpu/inference.env}"
PYTHON_BIN="${PYTHON_BIN:-python}"
STARTING_PID=""

umask 077
mkdir -p "$RUNTIME_DIR"

exec 9>"$LOCK_FILE"
if command -v flock >/dev/null 2>&1; then
  flock -n 9 || { echo "Another GPU service command is running." >&2; exit 1; }
fi

load_env_file() {
  [[ -f "$ENV_FILE" ]] || return 0
  local owner mode
  owner="$(stat -c '%u' "$ENV_FILE")"
  mode="$(stat -c '%a' "$ENV_FILE")"
  if [[ "$owner" != "$(id -u)" ]]; then
    echo "Refusing env file not owned by the current user: $ENV_FILE" >&2
    exit 1
  fi
  if (( (8#$mode & 077) != 0 )); then
    echo "Refusing env file with group/other permissions; run chmod 600 $ENV_FILE" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
}

load_env_file

service_pid() {
  awk 'NR == 1 { print $1 }' "$PID_FILE" 2>/dev/null
}

process_starttime() {
  awk '{ print $22 }' "/proc/$1/stat" 2>/dev/null
}

is_running() {
  [[ -s "$PID_FILE" ]] || return 1
  local pid recorded_start current_start cmdline
  read -r pid recorded_start <"$PID_FILE" || return 1
  [[ "$pid" =~ ^[0-9]+$ && "$recorded_start" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  current_start="$(process_starttime "$pid")"
  [[ -n "$current_start" && "$current_start" == "$recorded_start" ]] || return 1
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  cmdline="$(tr '\0' ' ' <"/proc/$pid/cmdline")"
  [[ "$cmdline" == *"scripts/gpu_inference_api.py"* ]]
}

cleanup_starting_process() {
  if [[ -n "$STARTING_PID" ]] && is_running; then
    kill "$STARTING_PID" 2>/dev/null || true
    for _ in $(seq 1 20); do
      is_running || break
      sleep 0.5
    done
    if is_running; then
      kill -KILL "$STARTING_PID" 2>/dev/null || true
      for _ in $(seq 1 10); do
        is_running || break
        sleep 0.2
      done
    fi
  fi
  if is_running; then
    echo "Could not stop startup process $(service_pid); keeping PID metadata." >&2
    return 1
  fi
  if [[ -n "$STARTING_PID" ]]; then
    wait "$STARTING_PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE" "$PORT_FILE"
}

start_service() {
  if is_running; then
    echo "GPU inference is already running (PID $(service_pid))."
    return 0
  fi

  export HOST="${HOST:-127.0.0.1}"
  export PORT="${PORT:-8005}"
  export MODEL_ID="${MODEL_ID:-google/medgemma-4b-it}"
  export LOCAL_FILES_ONLY="${LOCAL_FILES_ONLY:-true}"
  export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
  export HF_HUB_DISABLE_TELEMETRY="1"

  cd "$ROOT_DIR"
  nohup "$PYTHON_BIN" scripts/gpu_inference_api.py 9>&- </dev/null >>"$LOG_FILE" 2>&1 &
  local pid=$!
  local starttime
  starttime="$(process_starttime "$pid")"
  if [[ -z "$starttime" ]]; then
    kill "$pid" 2>/dev/null || true
    echo "Could not record the GPU service process." >&2
    return 1
  fi
  printf '%s %s\n' "$pid" "$starttime" >"$PID_FILE"
  printf '%s\n' "$PORT" >"$PORT_FILE"
  STARTING_PID="$pid"
  trap cleanup_starting_process INT TERM EXIT

  echo "Starting MedGemma on $HOST:$PORT (PID $pid)."
  for _ in $(seq 1 90); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "GPU inference stopped during startup. See $LOG_FILE" >&2
      cleanup_starting_process
      STARTING_PID=""
      trap - INT TERM EXIT
      return 1
    fi
    if "$PYTHON_BIN" -c "import json,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:${PORT}/healthz',timeout=2)); raise SystemExit(0 if data.get('status') == 'ok' else 1)" 2>/dev/null; then
      echo "GPU inference is ready: http://127.0.0.1:$PORT"
      STARTING_PID=""
      trap - INT TERM EXIT
      return 0
    fi
    sleep 2
  done

  echo "Startup timed out. See $LOG_FILE" >&2
  cleanup_starting_process
  STARTING_PID=""
  trap - INT TERM EXIT
  return 1
}

stop_service() {
  if ! is_running; then
    echo "GPU inference is not running."
    return 0
  fi
  local pid
  pid="$(service_pid)"
  kill "$pid"
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      rm -f "$PORT_FILE"
      echo "GPU inference stopped."
      return 0
    fi
    sleep 1
  done
  echo "PID $pid did not stop after SIGTERM; inspect it manually." >&2
  return 1
}

status_service() {
  if is_running; then
    local port="${PORT:-}"
    if [[ -z "$port" && -s "$PORT_FILE" ]]; then
      port="$(<"$PORT_FILE")"
    fi
    port="${port:-8005}"
    echo "GPU inference is running (PID $(service_pid))."
    "$PYTHON_BIN" -c "import json,urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:${port}/healthz',timeout=3)),ensure_ascii=False))"
  else
    echo "GPU inference is not running."
    return 1
  fi
}

case "${1:-status}" in
  start) start_service ;;
  stop) stop_service ;;
  restart) stop_service; start_service ;;
  status) status_service ;;
  logs) tail -n "${LINES:-100}" "$LOG_FILE" ;;
  *) echo "Usage: $0 {start|stop|restart|status|logs}" >&2; exit 2 ;;
esac
