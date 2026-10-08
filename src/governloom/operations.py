"""Explicit SQLite backup/restore and conservative observation retention."""

import argparse
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from urllib.parse import quote

from . import __version__
from .schemas import now, uid


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1_000_000), b""):
            result.update(block)
    return result.hexdigest()


def readonly(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError("Source database does not exist")
    return sqlite3.connect("file:" + quote(path.as_posix(), safe="/:") + "?mode=ro", uri=True, timeout=1)


def snapshot(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if source == destination or not source.is_file():
        raise ValueError("Choose an existing source and a separate new destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive reservation prevents overwriting an existing database.
    with destination.open("xb"):
        pass
    reader = writer = None
    try:
        reader, writer = readonly(source), sqlite3.connect(destination, timeout=1)
        deadline = time.monotonic() + 30
        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise TimeoutError("Database snapshot deadline exceeded")
        reader.backup(writer, pages=100, progress=progress, sleep=0.01)
        if writer.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity check failed")
        tables = {row[0] for row in writer.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"entities", "jobs", "results", "runtime_observations"}.issubset(tables):
            raise ValueError("Not a current GovernLoom database")
        counts = {table: writer.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                  for table in ("entities", "jobs", "results", "runtime_observations")}
    except BaseException:
        if writer:
            writer.close()
            writer = None
        destination.unlink(missing_ok=True)  # Only the file exclusively created above.
        raise
    finally:
        if reader:
            reader.close()
        if writer:
            writer.close()
    return counts


def backup(source, destination):
    destination = Path(destination).resolve()
    manifest = destination.with_suffix(destination.suffix + ".manifest.json")
    if manifest.exists():
        raise FileExistsError("Backup manifest already exists")
    counts = snapshot(source, destination)
    record = {"schema_version": 1, "governloom_version": __version__, "created_at": now(), "sha256": sha256(destination),
              "counts": counts, "integrity_check": "ok", "scope": "Full SQLite snapshot including audit and key hashes"}
    with manifest.open("x", encoding="utf-8") as target:
        json.dump(record, target, indent=2)
    return record


def restore(source, destination):
    source = Path(source).resolve()
    manifest = json.loads(source.with_suffix(source.suffix + ".manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or sha256(source) != manifest.get("sha256"):
        raise ValueError("Backup checksum/manifest mismatch")
    counts = snapshot(source, destination)
    if counts != manifest["counts"] or sha256(source) != manifest["sha256"] or sha256(destination) != manifest["sha256"]:
        Path(destination).resolve().unlink()  # This function exclusively created it.
        raise ValueError("Restored counts do not match snapshot manifest")
    return {"counts": counts, "integrity_check": "ok", "restored_from_sha256": manifest["sha256"]}


RETAINABLE = """
SELECT cursor FROM runtime_observations AS observation
WHERE received_at < ?
AND cursor != (SELECT max(cursor) FROM runtime_observations)
AND NOT EXISTS (SELECT 1 FROM entities AS alert WHERE kind='runtime_alert'
    AND alert.application_id=observation.application_id
    AND json_extract(alert.payload,'$.event_id')=observation.event_id)
AND NOT EXISTS (SELECT 1 FROM runtime_observations AS outcome
    WHERE outcome.application_id=observation.application_id
    AND json_extract(outcome.payload,'$.event.related_event_id')=observation.event_id)
"""


def retention(path, days, actor, apply=False):
    from datetime import datetime, timedelta, timezone
    if not isinstance(days, int) or not 1 <= days <= 3650 or not actor.strip() or len(actor) > 200:
        raise ValueError("Specify retention days 1..3650 and an actor")
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError("Database does not exist")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    connection = sqlite3.connect(path, timeout=1) if apply else readonly(path)
    try:
        connection.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
        count = connection.execute("SELECT count(*) FROM (" + RETAINABLE + ")", (cutoff,)).fetchone()[0]
        record = {"schema_version": 1, "id": uid(), "object_id": "runtime-retention", "revision": 1,
            "action": "runtime_retention_applied", "actor": actor, "created_at": now(),
            "value": {"days": days, "cutoff": cutoff, "eligible_observations": count,
                "scope": "Unalerted observations only; linked predictions, all alerts/audit/policies and newest cursor protected"}}
        if apply:
            from .monitoring import sanitize
            connection.execute("DELETE FROM runtime_observations WHERE cursor IN (" + RETAINABLE + ")", (cutoff,))
            connection.execute("INSERT INTO entities(id,kind,application_id,payload) VALUES(?,?,?,?)",
                (record["id"], "review_event", None, json.dumps(sanitize(record))))
        connection.commit()
        return {"applied": apply, **record["value"]}
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("backup", "restore"):
        command = commands.add_parser(name)
        command.add_argument("source")
        command.add_argument("destination", help="New file; existing destinations are refused")
    command = commands.add_parser("retention")
    command.add_argument("database")
    command.add_argument("--days", type=int, required=True)
    command.add_argument("--actor", required=True)
    command.add_argument("--apply", action="store_true", help="Explicitly execute deletion; default is a read-only preview")
    args = parser.parse_args()
    result = retention(args.database, args.days, args.actor, args.apply) if args.command == "retention" else globals()[args.command](args.source, args.destination)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
