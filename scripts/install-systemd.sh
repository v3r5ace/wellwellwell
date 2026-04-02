#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SERVICE_USER=""
WORKDIR="${REPO_ROOT}"
OUTPUT_DIR=""
NO_ENABLE=0

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
  ./scripts/install-systemd.sh [--user USER] [--workdir DIR] [--output-dir DIR] [--no-enable]

Options:
  --user USER       Linux user the services should run as
  --workdir DIR     Repo path on the target machine
  --output-dir DIR  Write unit files to a directory instead of /etc/systemd/system
  --no-enable       Do not run systemctl enable/start after writing unit files
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)
      SERVICE_USER="$2"
      shift 2
      ;;
    --workdir)
      WORKDIR="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --no-enable)
      NO_ENABLE=1
      shift
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

if [[ -z "${SERVICE_USER}" ]]; then
  if [[ -n "${SUDO_USER:-}" ]]; then
    SERVICE_USER="${SUDO_USER}"
  else
    SERVICE_USER="$(id -un)"
  fi
fi

if [[ "${SERVICE_USER}" == "root" ]]; then
  fail "Refusing to install services as root. Re-run as a normal user or pass --user."
fi

if [[ ! -d "${WORKDIR}" ]]; then
  fail "Workdir does not exist: ${WORKDIR}"
fi

if [[ ! -f "${WORKDIR}/.env" ]]; then
  fail "Missing ${WORKDIR}/.env. Run ./scripts/install.sh first."
fi

if [[ ! -x "${WORKDIR}/.venv/bin/wellwellwell" ]]; then
  fail "Missing ${WORKDIR}/.venv/bin/wellwellwell. Run ./scripts/install.sh first."
fi

if [[ -n "${OUTPUT_DIR}" ]]; then
  mkdir -p "${OUTPUT_DIR}"
  TARGET_DIR="$(cd "${OUTPUT_DIR}" && pwd)"
  NO_ENABLE=1
else
  TARGET_DIR="/etc/systemd/system"
fi

write_api_unit() {
  cat <<EOF > "${1}/wellwellwell-api.service"
[Unit]
Description=WellWellWell API and dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${WORKDIR}
EnvironmentFile=${WORKDIR}/.env
ExecStart=${WORKDIR}/.venv/bin/wellwellwell serve
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
}

write_collect_unit() {
  cat <<EOF > "${1}/wellwellwell-collect.service"
[Unit]
Description=WellWellWell one-shot collection
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
WorkingDirectory=${WORKDIR}
EnvironmentFile=${WORKDIR}/.env
ExecStart=${WORKDIR}/.venv/bin/wellwellwell collect
EOF
}

write_timer_unit() {
  cat <<'EOF' > "${1}/wellwellwell-collect.timer"
[Unit]
Description=Run WellWellWell collection every 15 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Unit=wellwellwell-collect.service
Persistent=true

[Install]
WantedBy=timers.target
EOF
}

if [[ "${TARGET_DIR}" == "/etc/systemd/system" ]]; then
  command -v sudo >/dev/null 2>&1 || fail "sudo is required to install systemd units"
  TEMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TEMP_DIR}"' EXIT

  log "Generating unit files"
  write_api_unit "${TEMP_DIR}"
  write_collect_unit "${TEMP_DIR}"
  write_timer_unit "${TEMP_DIR}"

  log "Installing unit files"
  sudo install -m 0644 "${TEMP_DIR}/wellwellwell-api.service" "${TARGET_DIR}/wellwellwell-api.service"
  sudo install -m 0644 "${TEMP_DIR}/wellwellwell-collect.service" "${TARGET_DIR}/wellwellwell-collect.service"
  sudo install -m 0644 "${TEMP_DIR}/wellwellwell-collect.timer" "${TARGET_DIR}/wellwellwell-collect.timer"

  if [[ "${NO_ENABLE}" -eq 0 ]]; then
    log "Reloading systemd and enabling services"
    sudo systemctl daemon-reload
    sudo systemctl enable --now wellwellwell-api.service
    sudo systemctl enable --now wellwellwell-collect.timer
  fi
else
  log "Writing unit files to ${TARGET_DIR}"
  write_api_unit "${TARGET_DIR}"
  write_collect_unit "${TARGET_DIR}"
  write_timer_unit "${TARGET_DIR}"
fi

printf '\nSystemd setup complete.\n'
printf 'Service user: %s\n' "${SERVICE_USER}"
printf 'Workdir: %s\n' "${WORKDIR}"
printf 'Unit files: %s\n' "${TARGET_DIR}"
