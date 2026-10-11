# Monitor expected numeric outcomes

Send an output event with a numeric `prediction` and an explicit, timezone-aware
`outcome_due_at`. The deadline must follow its `occurred_at` and be within ten
years. Choose the deadline from the application's actual feedback process.
This is opt-in; untracked predictions are not counted as successful outcomes.

```python
from datetime import datetime, timedelta, timezone

prediction = hook.emit(trace_id=trace_id, phase="output", task_type="forecasting",
    model_version=model_version, application_version=application_version,
    metrics={"prediction": predicted_value},
    outcome_due_at=datetime.now(timezone.utc) + timedelta(days=1))
```

Run `governloom monitor-worker` separately from the API and webhook worker.
It checks deadlines every second in bounded batches, persists one alert for each
overdue expectation and groups/escalates it through the prediction's frozen policy.
Multiple workers/restarts do not duplicate deadline alerts. Use `--once` for a
finite check. A missing outcome means missing evidence, not a wrong prediction
or zero error. Deadline alerts request flag/review, never automatic enforcement.
The policy can set `outcome_deadline_action` and `outcome_deadline_mitigation`.
The system reserves the rule ID `outcome_deadline`.

When a numeric actual arrives, send `phase="outcome"`, its `actual` metric and
`related_event_id` pointing to the prediction receipt's event ID. Keep the same
trace, task, environment, model and application versions. The collector derives
absolute error and resolves that expectation. An outcome without numeric `actual`
does not resolve it. Corrections can create new outcome events; the first matching
numeric actual establishes the coverage resolution time.

Late seconds measure receipt by the collector, not when the actual became
observable. Backfilled data can therefore be late. Eventual actuals resolve
coverage; they do not close incidents or prove mitigation. Operator review stays
separate. The dashboard and authenticated
`GET /api/applications/{id}/outcome-coverage` show pending/overdue/received counts,
bounded records and overdue expectations that await the worker.

At most 10,000 unresolved expectations per application are admitted; exceeding
the bound rejects the event transaction rather than silently omitting its coverage.
Resolved history has no automatic expiry. Observation retention protects tracked
prediction origins. Monitor storage and set operational retention/backup budgets.
This release tracks numeric actuals; arbitrary human-label/task-success feedback
needs an explicit application mapping and is not inferred automatically.
