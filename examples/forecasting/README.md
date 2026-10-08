# Historical CO2 forecaster

Download one explicit snapshot with `python -m examples.forecasting.download
data/miniapps/noaa.txt`. It retains NOAA's complete header and writes source URL,
retrieval time and SHA-256 beside the snapshot. Services never download data on
startup and ordinary CI uses a labeled synthetic parser/integration fixture.

Set NOAA_SNAPSHOT to that file, GOVERNLOOM_ENDPOINT to the collector, and
GOVERNLOOM_INGEST_KEY to this application's scoped key. Start locally:

```powershell
.\.venv\Scripts\python.exe -m uvicorn examples.forecasting.app:create_app --factory --host 127.0.0.1 --port 8102
```

GET `/manifest` and `/evaluation`; POST `/predict` with date YYYY-MM in 2021-2024
and scenario natural/offset_fault; POST `/outcomes` with the returned event_id.
The outcome comes from the same frozen snapshot, and is linked to the exact
prediction/model/trace. Interpolated or missing actuals stay unavailable.
POST `/fallback` with enabled, actor and rationale selects seasonal-naive for
subsequent predictions; it does not revise earlier predictions or claim improved
accuracy. GET `/investigations` shows flagged-outcome records in the app's own DB.

The model fits quadratic trend plus annual sine/cosine on at most 120 observed
months strictly before each forecast origin. Tolerance is the 90th percentile of
2019-2020 calibration absolute error; held-out 2021-2024 results use that frozen
tolerance with chronological refitting. A source snapshot taken later cannot
establish what data revisions were actually available at each historical date.
This is a chronological backtest on a fixed snapshot, not a real-time-vintage study.

NOAA Global Monitoring Laboratory and source-header contributors are credited.
The header explains interpolation and the 2022-2023 Mauna Loa/Maunakea site change.
[Dataset/attribution](https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt).
Natural errors and the explicit +20 ppm offset fault remain separate. This
mini project tests governance integration; it is not a climate modeling claim.
