#!/usr/bin/env bash
set -euo pipefail

PORT="${BACKEND_PORT:-8000}"
TARGET="${ANDROID_TARGET:-auto}"
OUTPUT_FILE="app/src/main/java/com/harmony/interviewlite/data/GeneratedConfig.kt"

cd "$(dirname "$0")/.."

find_adb() {
  if command -v adb >/dev/null 2>&1; then
    command -v adb
    return
  fi
  if [[ -n "${ANDROID_HOME:-}" && -x "${ANDROID_HOME}/platform-tools/adb" ]]; then
    echo "${ANDROID_HOME}/platform-tools/adb"
    return
  fi
  if [[ -n "${ANDROID_SDK_ROOT:-}" && -x "${ANDROID_SDK_ROOT}/platform-tools/adb" ]]; then
    echo "${ANDROID_SDK_ROOT}/platform-tools/adb"
    return
  fi
  if [[ -x "${HOME}/Library/Android/sdk/platform-tools/adb" ]]; then
    echo "${HOME}/Library/Android/sdk/platform-tools/adb"
    return
  fi
  echo ""
}

has_running_emulator() {
  local adb_path
  adb_path="$(find_adb)"
  [[ -n "${adb_path}" ]] || return 1
  "${adb_path}" devices 2>/dev/null | awk '$1 ~ /^emulator-/ && $2 == "device" { found=1 } END { exit found ? 0 : 1 }'
}

detect_wifi_device_macos() {
  networksetup -listallhardwareports 2>/dev/null | awk '
    /Hardware Port: Wi-Fi|Hardware Port: AirPort/ { found=1; next }
    found && /Device:/ { print $2; exit }
  '
}

detect_default_device_macos() {
  route get default 2>/dev/null | awk '/interface:/ { print $2; exit }'
}

detect_ip_macos() {
  local device
  device="$(detect_wifi_device_macos)"
  if [[ -n "${device}" ]]; then
    ipconfig getifaddr "${device}" 2>/dev/null || true
    return
  fi

  device="$(detect_default_device_macos)"
  if [[ -n "${device}" ]]; then
    ipconfig getifaddr "${device}" 2>/dev/null || true
  fi
}

detect_ip_linux() {
  ip route get 1.1.1.1 2>/dev/null | awk '{ for (i=1; i<=NF; i++) if ($i == "src") { print $(i+1); exit } }'
}

detect_ip() {
  case "$(uname -s)" in
    Darwin) detect_ip_macos ;;
    Linux) detect_ip_linux ;;
    *) echo "" ;;
  esac
}

case "${TARGET}" in
  emulator)
    HOST="10.0.2.2"
    ;;
  device)
    HOST="$(detect_ip | head -n 1 | tr -d '[:space:]')"
    ;;
  auto)
    if has_running_emulator; then
      HOST="10.0.2.2"
    else
      HOST="$(detect_ip | head -n 1 | tr -d '[:space:]')"
    fi
    ;;
  *)
    echo "Unsupported ANDROID_TARGET=${TARGET}; use auto, emulator, or device." >&2
    exit 2
    ;;
esac

if [[ -z "${HOST}" ]]; then
  HOST="10.0.2.2"
fi

BASE_URL="http://${HOST}:${PORT}"

cat > "${OUTPUT_FILE}" <<KOTLIN
package com.harmony.interviewlite.data

const val GeneratedBackendBaseUrl = "${BASE_URL}"
KOTLIN

echo "Generated backend base URL: ${BASE_URL}"
echo "Target mode: ${TARGET}"
echo "Updated: ${OUTPUT_FILE}"
