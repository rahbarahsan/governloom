# Owned tool-using application

A local TF-IDF/logistic regression model selects `search` or `delete_draft` from
repository-authored requests. GovernLoom discovers the tool telemetry and proposes
permission monitoring. The scripted owner confirms `search` as permitted.

Run `python -m examples.policy_testbed --directory data/my-policy-check` from the
repository with `examples/requirements.txt` installed. This also checks the actual
digit classifier. Add `--forecast-snapshot PATH` to include the existing NOAA
forecaster. There are no provider calls.

Both permitted and disallowed model-selected attempts go through the public hook.
GovernLoom flags the disallowed attempt. The application's separate read-only
authorization prevents deletion; a flag is not enforcement evidence. A deliberately
supplied `delete_draft` call is additionally tested as an engineering control and
reported separately from model-selected calls.

The small training/request sets are authored integration examples, not independent
agent evaluation data. No actual malicious deletion or external side effect occurs.
