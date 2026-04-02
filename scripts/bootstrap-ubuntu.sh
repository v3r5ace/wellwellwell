#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

INSTALL_SYSTEMD=1
RUN_APT=1
SERVICE_USER="${SERVICE_USER:-${SUDO_USER:-$(id -un)}}"

log() {
  printf '\n==> %s\n' "$1"
}

fail() {
  printf '\nERROR: %s\n' "$1" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/bootstrap-ubuntu.sh [--skip-apt] [--skip-systemd] [--user USER]

Examples:
  CAMERA_RTSP_URL='rtsps://protect-host-or-ip:7441/stream-token?enableSrtp' \
  WELL_CROP='1450,0,250,580' \
  WELL_EMPTY_Y='66' \
  WELL_FULL_Y='484' \
  ./scripts/bootstrap-ubuntu.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-apt)
      RUN_APT=0
      shift
      ;;
    --skip-systemd)
      INSTALL_SYSTEMD=0
      shift
      ;;
    --user)
      SERVICE_USER="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

if [[ "${SERVICE_USER}" == "root" ]]; then
  fail "Refusing to install app services as root. Use --user sysadmin or run as sysadmin."
fi

command -v python3 >/dev/null 2>&1 || fail "python3 is required"

if [[ "${RUN_APT}" -eq 1 ]]; then
  command -v apt-get >/dev/null 2>&1 || fail "apt-get is required for Ubuntu bootstrap"
  command -v sudo >/dev/null 2>&1 || fail "sudo is required for package installation"

  log "Installing Ubuntu packages"
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip ffmpeg git
fi

log "Installing Python app"
"${REPO_ROOT}/scripts/install.sh"

if [[ "${INSTALL_SYSTEMD}" -eq 1 ]] && command -v systemctl >/dev/null 2>&1; then
  log "Installing systemd services"
  "${REPO_ROOT}/scripts/install-systemd.sh" --user "${SERVICE_USER}" --workdir "${REPO_ROOT}"
fi

printf '\nBootstrap complete.\n'
printf 'Dashboard command: %s/.venv/bin/wellwellwell serve\n' "${REPO_ROOT}"
printf 'Collector command: %s/.venv/bin/wellwellwell collect\n' "${REPO_ROOT}"
