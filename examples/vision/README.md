# Digit recognition service

This mini application trains a 64-tree random forest on actual 8x8 handwritten
digits. It owns its model and review SQLite database, and sends selected telemetry
through the public GovernLoom Python hook. Model inputs are not sent to the collector.

From the repository root, install root dependencies/editable GovernLoom, then
`pip install -r examples/requirements.txt` using the same Python environment.
Example dependencies are separate from the collector wheel. Use Python 3.13 for
this pinned testbed environment.

Configure a collector connection and policy using its normal dashboard/API. Read
the confidence threshold from `DigitModel().manifest`; the threshold is selected
only on calibration data. Set a vision/output metric rule on confidence less
than that threshold, action review or block, and issue an ingestion key.

```powershell
$env:GOVERNLOOM_ENDPOINT = 'http://127.0.0.1:8000'
# Set GOVERNLOOM_INGEST_KEY to your application-scoped key in this terminal.
.\.venv\Scripts\python.exe -m uvicorn examples.vision.app:create_app --factory --host 127.0.0.1 --port 8101
```

Routes: GET `/manifest`, `/samples`, `/evaluation`, `/reviews`; POST `/predict`
with sample_id or 64 pixels, mode observe/enforce, optional sample corruption
none/occlusion/noise. POST `/outcomes` submits actual_label with original event_id.
POST `/reviews/{id}/resolve` records actor, rationale, corrected_label and
expected_revision. A blocked response contains no prediction; its result remains
in the application-owned review queue. Resolutions are operator assertions.

Data: Alpaydin and Kaynak (1998), Optical Recognition of Handwritten Digits,
UCI, DOI 10.24432/C50P49, CC BY 4.0.
[Dataset attribution](https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits).
The bundled sklearn subset is internally split 65/15/20 with fixed seeds; this
is not the original benchmark protocol. Calibration chooses a nominal 20% review
budget; held-out review/error/miss counts are reported without retuning.

Start with the isolated testbed runner when available. This service is for local
development; it has no public hosting or user accounts. Stop it with Ctrl+C.
