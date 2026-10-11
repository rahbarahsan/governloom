"""Offline full recovery bundles and conservative delivery-history retention."""
import argparse
import base64
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .operations import backup, readonly, restore, sha256
from .schemas import now, uid
from .service import checksum


def secret_references(database):
    with readonly(database) as connection:
        rows = connection.execute("SELECT payload FROM entities WHERE kind='webhook_destination'")
        references = {value for (payload,) in rows for key, value in json.loads(payload).items()
            if key in ("secret_ref", "previous_secret_ref") and value is not None}
    if any(not isinstance(value, str) or not value.isalnum() or len(value) > 128 for value in references):
        raise ValueError("Invalid signing-secret reference in database")
    return sorted(references)


def private_copy(source, target):
    content = Path(source).read_bytes()
    try:
        key = base64.b64decode(content.decode("ascii").removeprefix("whsec_"), validate=True)
    except (ValueError, UnicodeError):
        raise ValueError("Invalid signing-secret file") from None
    if len(key) != 32:
        raise ValueError("Invalid signing-secret length")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content); output.flush(); os.fsync(output.fileno())


def backup_bundle(database, secrets_directory, destination):
    """SQLite backup is consistent; only refs from that snapshot are copied.

    Pause configuration/key rotation while bundling. Failed/incomplete directories
    remain private for diagnosis and cannot be mistaken for a completed bundle.
    """
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, mode=0o700, exist_ok=False)
    snapshot = destination / "collector.db"
    record = backup(database, snapshot)
    references = secret_references(snapshot)
    (destination / "secrets").mkdir(mode=0o700)
    for reference in references:
        private_copy(Path(secrets_directory) / reference, destination / "secrets" / reference)
    manifest = {"schema_version": 1, "created_at": now(), "database_sha256": record["sha256"],
        "secret_hashes": {reference: sha256(destination / "secrets" / reference) for reference in references},
        "scope": "Full SQLite plus referenced current/retiring signing secrets; contains private credentials and evidence"}
    with (destination / "bundle.json").open("x", encoding="utf-8") as target:
        json.dump(manifest, target, indent=2)
    return {"complete": True, "database_sha256": record["sha256"], "secret_files": len(references), "counts": record["counts"]}


def restore_bundle(source, destination):
    """Verify everything before creating a new cutover directory; never overwrite."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    manifest = json.loads((source / "bundle.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or sha256(source / "collector.db") != manifest.get("database_sha256"):
        raise ValueError("Bundle database checksum mismatch")
    references = secret_references(source / "collector.db")
    if not isinstance(manifest.get("secret_hashes"), dict) or sorted(manifest["secret_hashes"]) != references:
        raise ValueError("Bundle signing-secret references differ")
    for reference in references:
        if sha256(source / "secrets" / reference) != manifest["secret_hashes"][reference]:
            raise ValueError("Bundle signing-secret checksum mismatch")
    destination.mkdir(parents=True, mode=0o700, exist_ok=False)
    result = restore(source / "collector.db", destination / "collector.db")
    (destination / "secrets").mkdir(mode=0o700)
    for reference in references:
        private_copy(source / "secrets" / reference, destination / "secrets" / reference)
        if sha256(destination / "secrets" / reference) != manifest["secret_hashes"][reference]:
            raise ValueError("Signing secret changed during restore; incomplete destination must not be activated")
    # Configuration/URLs and clock deadlines are restored, not rewritten. Never
    # auto-start network delivery or claim that a backup revokes exposed keys.
    return {**result, "secret_files": len(references), "complete": True,
        "next_step": "Configure restored SQLite/secret paths, inspect destinations and deadlines, then start workers explicitly"}


RETAINABLE_DELIVERIES = """
SELECT delivery.id FROM entities AS delivery
WHERE delivery.kind='webhook_delivery'
AND json_extract(delivery.payload,'$.status')='delivered'
AND json_extract(delivery.payload,'$.updated_at') < ?
AND EXISTS (SELECT 1 FROM entities AS incident WHERE incident.kind='runtime_incident'
    AND incident.id=json_extract(delivery.payload,'$.incident_id')
    AND json_extract(incident.payload,'$.status') IN ('mitigated','false_positive'))
ORDER BY delivery.id LIMIT ?
"""


def delivery_retention(database, days, actor, *, apply=False, limit=1000):
    if type(days) is not int or not 1 <= days <= 3650 or type(limit) is not int or not 1 <= limit <= 10_000 or not actor.strip() or len(actor) > 200:
        raise ValueError("Specify days 1..3650, limit 1..10000 and an actor")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    if not Path(database).is_file():
        raise ValueError("Database does not exist")
    connection = sqlite3.connect(database, timeout=1) if apply else readonly(database)
    try:
        connection.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
        identifiers = [row[0] for row in connection.execute(RETAINABLE_DELIVERIES, (cutoff, limit))]
        report = {"applied": apply, "cutoff": cutoff, "eligible_deliveries": len(identifiers), "limit": limit,
            "deleted_ids_sha256": checksum(identifiers), "scope": "Delivered history for closed incidents only; pending/inflight/dead letters, incidents, alerts, all audit and signing keys remain"}
        if apply:
            connection.executemany("DELETE FROM entities WHERE kind='webhook_delivery' AND id=?", [(identifier,) for identifier in identifiers])
            record = {"id": uid(), "object_id": "webhook-retention", "revision": 1, "created_at": now(),
                "action": "webhook_history_retention_applied", "actor": actor, "value": report}
            from .monitoring import sanitize
            connection.execute("INSERT INTO entities(id,kind,application_id,payload) VALUES(?,?,?,?)", (record["id"], "review_event", None, json.dumps(sanitize(record))))
        connection.commit()
        return report
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup_parser = commands.add_parser("backup-bundle")
    backup_parser.add_argument("database"); backup_parser.add_argument("secrets_directory"); backup_parser.add_argument("destination")
    restore_parser = commands.add_parser("restore-bundle")
    restore_parser.add_argument("source"); restore_parser.add_argument("destination")
    retention_parser = commands.add_parser("delivery-retention")
    retention_parser.add_argument("database"); retention_parser.add_argument("--days", type=int, required=True)
    retention_parser.add_argument("--actor", required=True); retention_parser.add_argument("--limit", type=int, default=1000)
    retention_parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.command == "backup-bundle":
        result = backup_bundle(args.database, args.secrets_directory, args.destination)
    elif args.command == "restore-bundle":
        result = restore_bundle(args.source, args.destination)
    else:
        result = delivery_retention(args.database, args.days, args.actor, apply=args.apply, limit=args.limit)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
