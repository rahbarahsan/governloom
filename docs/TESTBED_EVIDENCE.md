# Actual-model integration evidence

The [reviewed report](experiments/testbed-2026-10-08.json) records a completed
isolated run on 2026-10-08 UTC (2026-10-07 Toronto). Reproduce with the command in
[examples/README.md](../examples/README.md). It starts no customer services and
stops all owned processes after capture. The captured corpus precedes subsequent
delivery/incident additions; document hashes identify its actual retrieved text.

| System | Natural-model evidence | Monitoring/action evidence |
| --- | --- | --- |
| Vision | 342/360 correct, 18 errors | 69 withheld/reviewed, including 17 errors; one confident error missed; 52 correct predictions also flagged |
| Forecasting | 48 observed NOAA outcomes; MAE 0.75654 ppm, RMSE 0.95067 ppm; seasonal-naive MAE 2.59771 ppm | All 15 errors above the frozen 0.97433 ppm calibration tolerance flagged after outcome arrival |
| RAG | Three actual subscription answers over real repository passages: enforcement answer, partial retention abstention, refusal to invent medical approval | Natural citation membership checks clear; both declared response mutations withheld; unauthorized tool write blocked with no marker file |

Vision uses an internal split of the bundled UCI digit images, not the original
benchmark protocol. Its calibration review budget is 20%; actual held-out review
fraction is 19.17%. Error capture is 17/18; flag precision for errors is 17/69.
Twelve occluded and twelve noise inputs are separate controlled fault groups.
Low confidence is not a correctness label.

Forecasting replays the downloaded NOAA/Scripps snapshot chronologically using
only prior observed rows in each fit. The snapshot contains later revisions;
this is not a historical data-vintage simulation. All 48 held-out outcomes in
this snapshot are observed. Missing/interpolated outcomes are separately tested
in CI and never replaced with zero. A deliberate 20 ppm offset and subsequent
fallback are software fault/action checks, excluded from natural errors. The
fallback's selection does not establish a quality improvement.

RAG used exactly three successful CLI turns (`gpt-6.1-sol`, Codex 0.160.1), with
44,692 reported input tokens and 409 output tokens, including CLI overhead.
No reference labels entered generation prompts. The first partial abstention
exposes incomplete retrieved evidence; citation membership cannot establish
factual support. These exploratory answers have no independent human quality
labels, and no immutable backend model snapshot or monetary cost measurement.
Fault mutations consume no additional model requests.

All **1,246** events were accepted: vision 1,138 (including warmups, outcomes and
faults), forecasting 99, RAG 9. Repeated/warmup/fault requests do not increase the
360/48 independent natural-case denominators. Collector events retain no raw
text or pixels. Application-owned review/capture storage is separate and private.
The scripted review resolution checks persistence, not independent adjudication.

Sequential paired requests to the same vision HTTP service, after five warmup
pairs, measured hook-off p50/p95/p99 **47.47/59.43/71.45 ms**, hook-on
**132.93/170.03/224.43 ms**, and paired additional latency
**86.47/128.80/181.58 ms** over 360 pairs. These include HTTP and application
storage costs, not just detector CPU, and establish no production SLA.
Background observation is required where this inline overhead is unacceptable.

Before delivery stress testing, set engineering acceptance targets for this
machine: background enqueue p95 below 5 ms at 100 attempted events/second;
bounded queue/memory under overload; exact replays produce one event/alert set;
every terminal loss or still-pending request is visible. Record actual achieved
capacity and failures. Targets are local test gates, not customer guarantees.
