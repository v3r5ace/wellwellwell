# Camera to Detector Plan

This project now targets a local detector instead of a cloud model.

## Current recommendation

Use this pipeline:

`UniFi Protect snapshot or RTSP -> ffmpeg/raw JPEG -> fixed crop -> OpenCV blue-marker detection -> SQLite -> dashboard`

Why this is the right first version:

- the camera is fixed
- the cable path is fixed
- the target object is a known color
- the frame only needs one measurement every 15 minutes

That makes local CV much simpler and cheaper than calling a general-purpose vision model.

## Detection strategy

The detector in [`wellwellwell/detector.py`](/Users/lpaine/Documents/GitHub/wellwellwell/wellwellwell/detector.py) does four things:

1. Convert the cropped ROI to HSV.
2. Threshold for the blue marker color range.
3. Clean the result with morphology.
4. Score contours and choose the best marker candidate.

The computed water level is still deterministic:

`percent_full = ((marker_y - empty_y) / (full_y - empty_y)) * 100`

## When to upgrade

Only move beyond this if one of these becomes true:

- night scenes produce too many false detections
- reflections or weather regularly hide the marker
- the crop contains multiple similar blue objects

If that happens, the next step should be a small local detector trained on your own cropped frames, not a larger general-purpose model.
