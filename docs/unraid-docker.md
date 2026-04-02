# Unraid Docker Setup

This is now the recommended deployment path.

## What we are running

One container does both jobs:

- serves the dashboard on port `8000`
- runs the collector loop every 15 minutes inside the container

That is controlled by:

- `WELL_ENABLE_COLLECTOR=true`
- `WELL_COLLECT_INTERVAL_MINUTES=15`

## Persistent storage

Mount one host path into `/data` in the container.

Recommended host path:

- `/mnt/user/appdata/wellwellwell`

Inside that path, the app stores:

- `wellwellwell.sqlite3`
- `snapshots/raw/...`
- `snapshots/crop/...`
- `snapshots/debug/...`

## Build the image on Unraid

From the Unraid terminal:

```bash
cd /mnt/user/appdata
git clone <your-repo-url> wellwellwell-src
cd wellwellwell-src
docker build -t wellwellwell:local .
```

## Run with Docker CLI

Replace the placeholder RTSP URL with your actual UniFi Protect stream URL.

```bash
docker run -d \
  --name wellwellwell \
  --restart unless-stopped \
  -p 8000:8000 \
  -e WELL_DATA_DIR=/data \
  -e WELL_DB_PATH=/data/wellwellwell.sqlite3 \
  -e WELL_SNAPSHOTS_DIR=/data/snapshots \
  -e WELL_BIND_HOST=0.0.0.0 \
  -e WELL_BIND_PORT=8000 \
  -e WELL_ENABLE_COLLECTOR=true \
  -e WELL_COLLECT_INTERVAL_MINUTES=15 \
  -e WELL_COLLECT_ON_STARTUP=true \
  -e CAMERA_RTSP_URL='rtsps://protect-host-or-ip:7441/replace-with-your-stream-token?enableSrtp' \
  -e WELL_CROP='1470,150,220,450' \
  -e WELL_BLUE_HSV_LOWER='90,60,40' \
  -e WELL_BLUE_HSV_UPPER='140,255,255' \
  -e WELL_MIN_CONTOUR_AREA=80 \
  -e WELL_EMPTY_Y=40 \
  -e WELL_FULL_Y=360 \
  -e WELL_SAVE_DEBUG_IMAGES=true \
  -v /mnt/user/appdata/wellwellwell:/data \
  wellwellwell:local
```

Then open:

- `http://<unraid-ip>:8000`

## Run with Compose Manager

Use [`deploy/docker-compose.example.yml`](/Users/lpaine/Documents/GitHub/wellwellwell/deploy/docker-compose.example.yml) as your starting point.

Typical flow:

1. Copy it to `compose.yaml`
2. Replace the RTSP URL placeholder
3. Run `docker compose up -d --build`

## How scheduling works

The built-in collector loop aligns itself to wall-clock boundaries. With `15` minutes configured, it will collect at quarter-hour boundaries like:

- `10:00`
- `10:15`
- `10:30`
- `10:45`

If `WELL_COLLECT_ON_STARTUP=true`, it also does one immediate collection when the container starts.

## Useful commands

```bash
docker logs -f wellwellwell
docker exec -it wellwellwell wellwellwell collect
docker exec -it wellwellwell wellwellwell collect --image /data/snapshots/raw/sample.jpg
```

## Tuning flow

Use this order when dialing the detector in:

1. Confirm the crop contains the full travel path of the blue weight.
2. Confirm the latest debug image shows the chosen contour box in the right place.
3. Adjust `WELL_BLUE_HSV_LOWER` and `WELL_BLUE_HSV_UPPER` if it misses or grabs the wrong object.
4. Set `WELL_EXPECTED_MARKER_X` if there are competing blue objects in the crop.
5. Re-check `WELL_EMPTY_Y` and `WELL_FULL_Y` with known states.

## If you want two containers instead

You can also split the roles:

- API container: `wellwellwell serve`
- collector container: `wellwellwell collector-loop`

For Unraid, I still recommend the single-container `wellwellwell run` path first because it is simpler to operate.
