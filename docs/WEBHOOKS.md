# Signed incident delivery

Register an incident receiver in **Monitoring → Incident delivery**. Operators
can create/disable destinations and replay failed deliveries for assigned
applications; reviewers/viewers can inspect delivery state. The API enforces the
same permissions and records the authenticated actor. No notification worker
starts automatically when the collector starts.

## Configure the collector host

Allow exact receiver URLs and choose a private signing-secret directory on both
the API and worker processes. For example in PowerShell:

```powershell
$env:GOVERNLOOM_WEBHOOK_ALLOWLIST = "https://your-receiver.example/incidents"
$env:GOVERNLOOM_WEBHOOK_SECRETS = "data/private-webhook-secrets"
.venv\Scripts\python.exe -m governloom.cli webhook-worker
```

Use `--db sqlite:///path/to/collector.db` before `webhook-worker` for another
database. The API and worker must use the same database, allowlist and secret
directory. `webhook-worker --once` processes one bounded dispatch cycle. Restart
both processes after changing host configuration. Remote receivers require HTTPS;
explicit `http://127.0.0.1:<port>/incidents` allows owned development receivers.

HTTPS hostnames must resolve exclusively to public IP addresses. Each attempt
resolves/validates all answers and dials one validated address with original TLS
hostname verification and Host. Proxies and redirects are not followed. Operators
cannot register a URL outside the host allowlist. This does not replace network
egress controls on a remotely hosted collector.

## Receiver contract

Connection returns one `whsec_...` signing secret, shown once. Configure it
privately in the receiver. Server secrets are readable only from the private host
directory, not list/export/audit responses. Protect that directory with OS access
controls, including explicit NTFS permissions on Windows. Back it up separately
from SQLite; a missing key causes visible delivery failure. To replace a key,
disable the old destination, create a new connection and configure the new secret.
There is no seamless key-rotation API in this release.

Each POST has Standard Webhooks 1.0 headers:

```text
webhook-id: <stable delivery ID>
webhook-timestamp: <current attempt's integer Unix seconds>
webhook-signature: v1,<base64 HMAC-SHA256>
```

The signed bytes are `id + "." + timestamp + "." + raw_request_body`, using the
32-byte base64-decoded secret. Verify with constant-time comparison, reject stale
timestamps (the example permits 300 seconds), then parse JSON. Keep clocks aligned.
`governloom.webhooks.verify_webhook` provides the Python verifier.

```json
{
  "schema_version": 1,
  "type": "governloom.incident.escalated",
  "id": "stable-delivery-id",
  "timestamp": "2026-10-10T12:00:00+00:00",
  "data": {
    "application_id": "application-id",
    "incident_id": "incident-id",
    "count": 3,
    "severity": "high"
  }
}
```

Notifications exclude prompts, passages, reviewer identities and credentials.
Fetch further evidence through a separately authenticated, application-scoped API
client. Persist the ID and body digest with receiver-side processing; reject
different bodies under an existing ID. The bundled
`examples.signed_receiver:create_app` demonstrates durable SQLite deduplication.

Return a **2xx** only after durable acceptance. A timeout, 408/425/429 or 5xx
retries with exponential backoff/jitter and Retry-After. Redirects and other
statuses terminate visibly. The receiver may see repeated HTTP requests: delivery
is at least once; exactly-once business processing requires its own transaction.

## Durability and failure states

An escalation transaction freezes one delivery/body per active destination. It
does no network I/O. The policy's escalation count/cooldown controls when these
notifications are produced; registering a destination does not backfill history.

A separate worker claims a fenced lease, persists the attempt before network I/O,
then records its result. Restarted workers recover expired leases. Defaults are
eight attempts and a 24-hour age bound; a server hint beyond the deadline becomes
a terminal failure. There are at most 1,000 pending/in-flight deliveries per
application and 20 active destinations; capacity overflow is visible as a
dead letter. Terminal/audit history grows and needs an operator-controlled storage
and retention policy. Logical bounds are not a disk quota.

States are `pending`, `delivering`, `delivered`, and `dead_letter`. Operators can
replay a dead letter with its current revision after repairing the receiver. Replay
retains the ID/body and lifetime attempt count, starts a new bounded attempt cycle,
and records the actor. A disabled destination cannot replay. An already in-flight
network request cannot be recalled by disabling its destination.

Delivery confirmation leaves the incident's disposition unchanged. Application
action acknowledgments, linked outcomes and operator verification are separate
evidence. Inspect them before recording mitigation.

Primary references checked 2026-10-10:
[Standard Webhooks 1.0](https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md)
and [OWASP SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
