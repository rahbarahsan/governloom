# Signing secrets, history and full recovery

Use [signing-key rotation](WEBHOOKS.md) for a receiver's current key. Planned
rotation has a bounded dual-signature overlap; emergency zero overlap revokes
prior signing generations. Update the receiver's private key configuration;
an already in-flight send cannot be recalled. This does not rotate ingestion keys.

Database-only backup remains available in [pilot operations](PILOT_OPERATIONS.md).
For a complete configured receiver restore, pause configuration/rotation and use:

```sh
python -m governloom.recovery backup-bundle data/collector.db data/secrets data/new-backup
python -m governloom.recovery restore-bundle data/new-backup data/new-restored
```

Both destination directories must be new. The bundle contains a consistent SQLite
snapshot, its integrity/count/checksum manifest, referenced current/retiring key
files and a manifest of secret-file hashes. It contains private evidence and
credentials: keep it private, encrypt/protect backups according to your host
policy and configure explicit NTFS permissions on Windows. Unix bundle directories
are created with owner-only access; key files use owner-only creation mode.
There is no encryption-at-rest service in this utility.

Restore verifies database and key checksums before creating the destination and
copies keys privately. It verifies copied keys too. Failed/incomplete directories
remain for private diagnosis; do not activate them. Restore does not start workers,
modify endpoints or extend delivery deadlines. Point `GOVERNLOOM_DB` at
`new-restored/collector.db` and `GOVERNLOOM_WEBHOOK_SECRETS` at
`new-restored/secrets`, inspect access/destinations, then explicitly start services.
Receiver deduplication state needs its own backup. Key authorization is restored
from the snapshot; revoke/rotate before delivery when restoring an older snapshot
that predates a compromise. Restoring a file does not revoke exposed credentials.

## Conservative delivery retention

Nothing is deleted automatically. Preview a bounded batch:

```sh
python -m governloom.recovery delivery-retention data/collector.db --days 60 --actor operator
```

`--apply` explicitly deletes eligible delivered-notification history and writes a
retention audit containing cutoff, count and an ID-list checksum. Only deliveries
completed before the cutoff for an incident already marked `mitigated` or
`false_positive` qualify. Pending/inflight deliveries, dead letters, open incidents,
alerts, all audit and signing keys remain. Default batch limit is 1,000, maximum
10,000; repeat preview/apply deliberately for larger histories. Replayable dead
letters are preserved. Deleted delivered bodies/history cannot be queried afterward.

Observation retention also protects all tracked prediction origins. This is a
conservative storage policy, not a total disk quota: unresolved expectations,
resolved history, audit, dead letters and retired key files still need host
monitoring and an explicit archival policy. SQLite freed pages are reusable; there
is no automatic VACUUM. A real `SQLITE_FULL` page-cap drill verifies transaction
rollback and exact event recovery without filling the operating system disk.

The [v0.5 evidence](V05_EVIDENCE.md) records an owned signed-retry/rotation/deadline
workflow and full bundle recovery. These finite drills do not establish sustained
production availability or recovery objectives.
