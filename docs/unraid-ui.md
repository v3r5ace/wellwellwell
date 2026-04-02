# Unraid UI Deployment

This is the cleanest no-shell path once the repo is public on GitHub.

## Recommended setup

Use a public GitHub repo plus GitHub Container Registry:

1. Push this repo to GitHub as `OWNER/REPO`
2. Let GitHub Actions publish `ghcr.io/OWNER/REPO:latest`
3. In Unraid, create the container from the WebUI

Why this path:

- no Ubuntu box required
- no manual `docker build` on Unraid after the first GitHub setup
- updates become normal image updates in Unraid
- everything stays manageable from the Docker tab

## What is already in the repo

- [`/.github/workflows/publish-ghcr.yml`](/Users/lpaine/Documents/GitHub/wellwellwell/.github/workflows/publish-ghcr.yml): builds and publishes the image to GHCR on push to `main`
- [`/unraid/wellwellwell.xml`](/Users/lpaine/Documents/GitHub/wellwellwell/unraid/wellwellwell.xml): Unraid template file
- [`/ca_profile.xml`](/Users/lpaine/Documents/GitHub/wellwellwell/ca_profile.xml): optional metadata if you later want to submit to Community Applications

## Option A: Pure WebUI, no template import

This is the simplest route today.

In Unraid:

1. Go to `Docker`
2. Click `Add Container`
3. Turn on advanced view if needed
4. Fill in these fields

Core fields:

- `Name`: `WellWellWell`
- `Repository`: `ghcr.io/OWNER/REPO:latest`
- `Network Type`: `Bridge`
- `WebUI`: `http://[IP]:[PORT:8000]/`

Port:

- Host port `8000` -> container port `8000`

Path mapping:

- Host path: `/mnt/user/appdata/wellwellwell`
- Container path: `/data`

Environment variables:

- `WELL_DATA_DIR=/data`
- `WELL_DB_PATH=/data/wellwellwell.sqlite3`
- `WELL_SNAPSHOTS_DIR=/data/snapshots`
- `WELL_ENABLE_COLLECTOR=true`
- `WELL_COLLECT_INTERVAL_MINUTES=15`
- `WELL_COLLECT_ON_STARTUP=true`
- `CAMERA_RTSP_URL=rtsps://protect-host-or-ip:7441/your-stream-token?enableSrtp`
- `WELL_CROP=1470,150,220,450`
- `WELL_BLUE_HSV_LOWER=90,60,40`
- `WELL_BLUE_HSV_UPPER=140,255,255`
- `WELL_MIN_CONTOUR_AREA=80`
- `WELL_EMPTY_Y=40`
- `WELL_FULL_Y=360`
- `WELL_SAVE_DEBUG_IMAGES=true`

After creation, the dashboard should be at:

- `http://<unraid-ip>:8000`

## Option B: Use the included Unraid template

If you want the UI form prebuilt:

1. Edit [`/unraid/wellwellwell.xml`](/Users/lpaine/Documents/GitHub/wellwellwell/unraid/wellwellwell.xml) and replace `REPLACE_ME_GITHUB_OWNER` plus `REPLACE_ME_GITHUB_REPO`
2. Copy that XML into your Unraid `templates-user` directory:
   `/boot/config/plugins/dockerMan/templates-user/`
3. In Unraid, go to `Docker`
4. Click `Add Container`
5. Select `WellWellWell` from the template list

This is still a good path, but it usually requires one manual file copy unless the template is later accepted into Community Applications.

## GitHub steps

Once the repo is public:

1. Push to the `main` branch
2. Open GitHub `Actions`
3. Confirm the `Publish Docker Image` workflow succeeds
4. Verify the package exists at:
   `https://github.com/OWNER/REPO/pkgs/container/REPO`

If the package is not visible, ensure:

- the repo is public
- Actions are enabled
- the package is public or accessible to your pull target

## Updating

After you push changes to `main`, GitHub Actions will publish a new `latest` image.

In Unraid, use the normal container update flow from the Docker tab.
