# Third-Party Notices

## Krunk mannequin geometry

The 3D pose-comparison figure (`frontend/assets/krunk-parts.json`) is derived
from a user-supplied humanoid STL model ("Brave Krunk"). Only a decimated,
re-rigged low-poly geometry is committed; the original STL is not distributed
with this project. `tools/segment_krunk.py` regenerates the asset from the
source STL. If you redistribute this project, confirm you have the right to use
the original model's likeness.

## MediaPipe Tasks Vision

This project includes `@mediapipe/tasks-vision` version `0.10.35` and the official Pose Landmarker Lite, Pose Landmarker Full (used by the high-accuracy mode for low-quality footage), and Hand Landmarker model assets.

- Project: https://github.com/google-ai-edge/mediapipe
- Web documentation: https://ai.google.dev/edge/mediapipe/solutions/guide
- License: Apache License 2.0

Included files are stored under:

- `frontend/vendor/mediapipe`
- `frontend/models`

## Three.js

This project includes `three.js` version `0.160.0` (minified ES module build), used to render the 3D pose comparison and correct-form demo.

- Project: https://github.com/mrdoob/three.js
- License: MIT License

Included files are stored under:

- `frontend/vendor/three`

## qrcode-generator

This project includes `qrcode-generator` version `1.4.4`, used to render the in-page "Generate QR code" share link entirely on-device (no external QR API).

- Project: https://github.com/kazuhikoarase/qrcode-generator
- License: MIT License

Included files are stored under:

- `frontend/vendor/qrcode`

The original VolleyForm UI artwork under `frontend/assets` was generated specifically for this project and contains no third-party watermark or brand mark.
