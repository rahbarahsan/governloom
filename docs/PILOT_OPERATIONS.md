# Private pilot operations

This checkpoint supplies explicit backup/restore, conservative retention and
local delivery measurements. It has not been deployed or tested as a hosted
multi-user service. See [actual-model evidence](TESTBED_EVIDENCE.md).

## Backup and restore

Use new destination files from the repository root:

```powershell
.\.venv\Scripts\python.exe -m governloom.operations backup data/governloom.db data/backups/new-snapshot.db
.\.venv\Scripts\python.exe -m governloom.operations restore data/backups/new-snapshot.db data/recovered.db
```

Backup uses SQLite's online backup API to include committed WAL data, checks
integrity and writes SHA-256/count metadata. Restore verifies the manifest,
copied checksum, integrity and counts; existing destinations are refused.
Snapshot deadline is 30 seconds. See [Python backup documentation](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup)
and [SQLite backup design](https://www.sqlite.org/backup.html).

The actual testbed backup/restore preserved **1,246 observations and 130 entities**,
integrity `ok`, SHA-256
`ab801b1d732aef697732191f275f4725b6133c45fc5fb55145008be88cf3b899`.
Live-WAL tests also preserve policy/incident/audit evidence, key hashes and exact
replay identity. Backups include private source/review data; keep them private.

To use a restored file, stop collector/worker, change `GOVERNLOOM_DB` to its SQLite
URL, start and verify health/evidence before resuming traffic. Restore preserves
active key hashes; retain/rotate serving credentials via normal APIs. No restore
was applied to the user's normal workbench database.

## Retention

Nothing is deleted automatically. Preview first:

```powershell
.\.venv\Scripts\python.exe -m governloom.operations retention data/governloom.db --days 60 --actor "Private pilot operator"
```

Explicit `--apply` executes the selection transactionally and audits it. Only
old **unalerted observations** without incoming outcome references are eligible.
Alerts, incidents, actions, policies, audit, legacy evaluation data and linked
predictions stay protected. The newest observation protects the cursor watermark
on existing schemas. Deleting an old outcome can release its prediction for a
later pass. Tests prove preview is non-mutating and references/cursors survive.

This does not bound all history or implement customer-specific erasure/legal
holds. Agree those policies before using sensitive production data; broader
retention is future work. Freed space is reusable, with no automatic VACUUM.

## Measured capacity

Install optional example dependencies, then:

```powershell
.\.venv\Scripts\python.exe -m examples.capacity --output data/new-capacity-capture
```

[Reviewed local report](experiments/capacity-2026-10-08.json): all 100 events
attempted at 100/second accepted; enqueue p50/p95/p99
**0.159/0.449/0.568 ms**, meeting the preset 5 ms p95 gate. An unpaced 1,000-event
burst with queue bound 16 accepted 16, dropped 984, and peaked at 7,936 serialized
bytes. All 116 accepted events have collector records and grouped into one
incident/one cooldown-limited escalation. Drain left no pending event/worker;
the owned collector stopped.

These short transport measurements use controlled telemetry; they are not
sustained throughput, total memory, model accuracy or an availability SLA.
Tests cover outage/restart, committed receipt loss, overflow, authentication
failure and incomplete drain. SQLite single-writer behavior and larger histories
require workload-specific capacity studies.

## TLS outline (not deployed)

Build the web bundle, run the API on loopback and keep administration on a private
network. Bootstrap [named accounts](OPERATOR_ACCESS.md) and use operator mode.
Set `GOVERNLOOM_ALLOWED_HOSTS` to the chosen domain plus loopback, and
`GOVERNLOOM_ALLOWED_ORIGINS` to the exact HTTPS dashboard origin. Ingest agents
use scoped keys, never operator session tokens.

Example Caddyfile for a domain the operator owns:

```caddyfile
collector.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Caddy can manage certificates when DNS/challenge reachability requirements are
met. Configure the chosen environment using [automatic HTTPS](https://caddyserver.com/docs/automatic-https)
and [reverse proxy documentation](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
Keep the backend port private; SDK remote URLs require HTTPS and reject
redirects. This outline has not been deployed or TLS-tested here.

## Identity and remaining access boundaries

Named accounts now supply audited actors, revocable sessions and explicit
viewer/reviewer/operator/admin application scopes. Legacy local mode still uses
asserted actors. Owner names and operator verification remain attestations.
Offline backup/restore uses host filesystem privileges, not API accounts.
SSO/MFA, organization/tenant isolation, external notifications and independent
action verification remain future work. The opt-in metadata outbox survives
restarts; raw text cannot be replayed from it. See [access](OPERATOR_ACCESS.md)
and [delivery](RUNTIME_DELIVERY.md) for exact bounds.
No paid provider calls, deployment or real recipients are needed for this testbed.
