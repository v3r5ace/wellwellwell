# WellWellWell

Local-first well water level monitoring for a fixed UniFi G5 Pro camera.

This version is now Docker-first for Unraid:

1. Grab one frame every 15 minutes from UniFi Protect over RTSP or a snapshot URL.
2. Crop the small region that contains the cable and marker weight.
3. Detect the marker weight locally with OpenCV.
4. Convert the marker position into `% full` with a one-time calibration.
5. Estimate gallons remaining from a full-capacity value.
6. Store the readings in SQLite and show them in a fast local web dashboard.

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- OpenCV + NumPy
- SQLite
- Static HTML/CSS/JS dashboard
- Docker image with `ffmpeg`
- Optional built-in collector loop for single-container deployment

## Repo layout

- [`Dockerfile`](/Users/lpaine/Documents/GitHub/wellwellwell/Dockerfile): Docker image for Unraid or any Docker host
- [`.github/workflows/publish-ghcr.yml`](/Users/lpaine/Documents/GitHub/wellwellwell/.github/workflows/publish-ghcr.yml): publish `ghcr.io/<owner>/wellwellwell` from GitHub Actions
- [`deploy/docker-compose.example.yml`](/Users/lpaine/Documents/GitHub/wellwellwell/deploy/docker-compose.example.yml): single-container example with built-in collector
- [`docs/unraid-docker.md`](/Users/lpaine/Documents/GitHub/wellwellwell/docs/unraid-docker.md): recommended Unraid deployment path
- [`docs/unraid-ui.md`](/Users/lpaine/Documents/GitHub/wellwellwell/docs/unraid-ui.md): pure WebUI deployment path
- [`unraid/wellwellwell.xml`](/Users/lpaine/Documents/GitHub/wellwellwell/unraid/wellwellwell.xml): Unraid template file
- [`wellwellwell/cli.py`](/Users/lpaine/Documents/GitHub/wellwellwell/wellwellwell/cli.py): `init-db`, `collect`, `serve`, `collector-loop`, and `run`
- [`wellwellwell/runtime.py`](/Users/lpaine/Documents/GitHub/wellwellwell/wellwellwell/runtime.py): wall-clock-aligned collector loop
- [`wellwellwell/capture.py`](/Users/lpaine/Documents/GitHub/wellwellwell/wellwellwell/capture.py): snapshot and RTSP frame ingest
- [`wellwellwell/detector.py`](/Users/lpaine/Documents/GitHub/wellwellwell/wellwellwell/detector.py): blue-marker detector
- [`wellwellwell/api.py`](/Users/lpaine/Documents/GitHub/wellwellwell/wellwellwell/api.py): API + dashboard server

## Unraid fast path

Use the guide in [`docs/unraid-docker.md`](/Users/lpaine/Documents/GitHub/wellwellwell/docs/unraid-docker.md).

At a high level:

1. Build the Docker image on your Unraid host.
2. Mount `/mnt/user/appdata/wellwellwell:/data`.
3. Set `WELL_ENABLE_COLLECTOR=true`.
4. Set your `CAMERA_RTSP_URL`, `WELL_CROP`, `WELL_EMPTY_Y`, and `WELL_FULL_Y`.
5. Run the container and open port `8000`.

If you want to stay entirely in the Unraid WebUI after the repo is public, use [`docs/unraid-ui.md`](/Users/lpaine/Documents/GitHub/wellwellwell/docs/unraid-ui.md). That path uses GitHub Actions to publish the image and then installs it from Unraid’s Docker UI.

## Environment variables

The main variables are:

- `CAMERA_RTSP_URL` or `CAMERA_SNAPSHOT_URL`
- `WELL_CROP`
- `WELL_EMPTY_Y`
- `WELL_FULL_Y`
- `WELL_FULL_GALLONS`
- `WELL_ENABLE_COLLECTOR`
- `WELL_COLLECT_INTERVAL_MINUTES`
- `WELL_COLLECT_ON_STARTUP`
- `WELL_FLUSH_PASSWORD`
- `WELL_DATA_DIR`
- `WELL_DB_PATH`
- `WELL_SNAPSHOTS_DIR`

See [`.env.example`](/Users/lpaine/Documents/GitHub/wellwellwell/.env.example) for the full set.

## Local Python dev

If you still want to run it outside Docker:

```bash
./scripts/install.sh
wellwellwell collect --image "/path/to/sample.jpg"
wellwellwell serve
```

## Calibration

The app stores the marker center `y` in crop-relative pixels.

- `WELL_EMPTY_Y`: marker position when the well is empty
- `WELL_FULL_Y`: marker position when the well is full

The code computes:

`percent_full = ((marker_y - empty_y) / (full_y - empty_y)) * 100`

Gallons remaining are estimated as:

`gallons_remaining = percent_full * WELL_FULL_GALLONS / 100`

Because your float mechanism is inverted, larger `y` means the marker is lower in the frame and the well is fuller.

## Admin actions

If `WELL_FLUSH_PASSWORD` is set, the dashboard exposes a password-protected `Flush History` button that deletes:

- all stored readings from SQLite
- all generated raw, crop, and debug snapshots under `/data/snapshots`

## Detection notes

The detector is intentionally narrow:

- threshold blue in HSV
- clean the mask with morphology
- find contours
- score candidates by area, aspect ratio, fill ratio, and horizontal position

That is much easier to tune and run locally than a general-purpose model for this camera angle.

## Legacy Ubuntu path

The older Ubuntu/systemd setup is still documented in [`docs/ubuntu-setup.md`](/Users/lpaine/Documents/GitHub/wellwellwell/docs/ubuntu-setup.md), but Unraid + Docker is now the recommended deployment target.
