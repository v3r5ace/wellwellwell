#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
ENV_EXAMPLE="${REPO_ROOT}/.env.example"
ENV_FILE="${REPO_ROOT}/.env"

set_env_value() {
  local key="$1"
  local value="$2"
  local escaped_value

  escaped_value="${value//\\/\\\\}"
  escaped_value="${escaped_value//&/\\&}"
  escaped_value="${escaped_value//|/\\|}"

  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i.bak "s|^${key}=.*$|${key}=${escaped_value}|" "${ENV_FILE}"
    rm -f "${ENV_FILE}.bak"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${ENV_FILE}"
  fi
}

apply_optional_env_overrides() {
  local keys=(
    CAMERA_SNAPSHOT_URL
    CAMERA_RTSP_URL
    CAMERA_USERNAME
    CAMERA_PASSWORD
    WELL_CROP
    WELL_BLUE_HSV_LOWER
    WELL_BLUE_HSV_UPPER
    WELL_MIN_CONTOUR_AREA
    WELL_EXPECTED_MARKER_X
    WELL_EMPTY_Y
    WELL_FULL_Y
    WELL_SAVE_DEBUG_IMAGES
    WELL_BIND_HOST
    WELL_BIND_PORT
    WELL_DATA_DIR
    WELL_DB_PATH
    WELL_SNAPSHOTS_DIR
    FFMPEG_PATH
    FFMPEG_RTSP_TRANSPORT
  )

  local key
  for key in "${keys[@]}"; do
    if [[ -n "${!key-}" ]]; then
      set_env_value "${key}" "${!key}"
    fi
  done
}

log() {
  printf '\n==> %s\n' "$1"
}

fail() {
  printf '\nERROR: %s\n' "$1" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 is required"

if ! python3 -m venv --help >/dev/null 2>&1; then
  fail "python3-venv is required. On Ubuntu run: sudo apt install -y python3-venv"
fi

log "Creating virtual environment"
python3 -m venv "${VENV_DIR}"

log "Upgrading pip"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip

log "Installing WellWellWell"
"${VENV_DIR}/bin/pip" install -e "${REPO_ROOT}"

if [[ ! -f "${ENV_FILE}" ]]; then
  log "Creating .env from .env.example"
  cp "${ENV_EXAMPLE}" "${ENV_FILE}"
else
  log ".env already exists, leaving it in place"
fi

log "Applying environment overrides"
apply_optional_env_overrides

log "Initializing database"
"${VENV_DIR}/bin/wellwellwell" init-db

printf '\nSetup complete.\n'
printf 'Next steps:\n'
printf '1. Edit %s\n' "${ENV_FILE}"
printf '2. Test a sample image: %s collect --image "/path/to/sample.jpg"\n' "${VENV_DIR}/bin/wellwellwell"
printf '3. Start the dashboard: %s serve\n' "${VENV_DIR}/bin/wellwellwell"
