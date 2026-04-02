# Ubuntu 24.04 Setup

These steps assume a fresh Ubuntu Server 24.04 LTS machine.

The examples below assume:

- Linux user: `sysadmin`
- repo path: `/home/sysadmin/wellwellwell`
- UniFi Protect secure RTSP stream via `CAMERA_RTSP_URL`

## 1. Base packages

Most automated path:

```bash
CAMERA_RTSP_URL='rtsps://protect-host-or-ip:7441/your-stream-token?enableSrtp' \
WELL_CROP='1450,0,250,580' \
WELL_EMPTY_Y='66' \
WELL_FULL_Y='484' \
./scripts/bootstrap-ubuntu.sh --user sysadmin
```

That single command handles package install, app install, `.env` bootstrapping, DB setup, and `systemd` service installation.

If you want the manual steps instead, continue below.

## 1a. Base packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg git
```

## 2. Clone the repo

```bash
git clone <your-repo-url> ~/wellwellwell
cd ~/wellwellwell
```

## 3. Python environment

Fastest path:

```bash
./scripts/install.sh
```

That handles the venv, pip upgrade, editable install, `.env` bootstrap, and DB initialization.

If you want the manual steps instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

## 4. App configuration

```bash
cp .env.example .env
```

Edit `.env` and set:

- `CAMERA_RTSP_URL` or `CAMERA_SNAPSHOT_URL`
- `WELL_CROP`
- `WELL_EMPTY_Y`
- `WELL_FULL_Y`

For your current camera, set `CAMERA_RTSP_URL` to the full Protect `rtsps://...:7441/...` URL in `.env`.

If your UniFi Protect path is RTSP-based, test a one-shot capture:

```bash
source .venv/bin/activate
wellwellwell collect --image "/path/to/known-good-sample.jpg"
```

Then test against the live camera:

```bash
source .venv/bin/activate
set -a
source .env
set +a
wellwellwell collect
```

## 5. Start the dashboard

```bash
source .venv/bin/activate
set -a
source .env
set +a
wellwellwell serve
```

Visit `http://<machine-ip>:8000`.

## 6. Install systemd units

Fastest path:

```bash
./scripts/install-systemd.sh --user sysadmin
```

That script generates the unit files with the correct user and repo path, installs them into `/etc/systemd/system`, reloads `systemd`, and enables the API service plus the 15-minute timer.

If you want to inspect generated units without installing them:

```bash
./scripts/install-systemd.sh --user sysadmin --output-dir /tmp/wellwellwell-units
```

If you prefer the manual service commands instead:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now wellwellwell-api.service
sudo systemctl enable --now wellwellwell-collect.timer
```

Useful commands:

```bash
sudo systemctl status wellwellwell-api.service
sudo systemctl status wellwellwell-collect.timer
sudo journalctl -u wellwellwell-api.service -f
sudo journalctl -u wellwellwell-collect.service -f
```

## 7. Tuning flow

Use this order when dialing the detector in:

1. Confirm the crop contains the full travel path of the marker weight.
2. Confirm the latest debug image shows the chosen contour box in the right place.
3. Adjust `WELL_MARKER_HSV_LOWER` and `WELL_MARKER_HSV_UPPER` if it misses or grabs the wrong object.
4. Set `WELL_EXPECTED_MARKER_X` if there are competing colored objects in the crop.
5. Re-check `WELL_EMPTY_Y` and `WELL_FULL_Y` with known states.
