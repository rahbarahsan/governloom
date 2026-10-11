import argparse
import json
from pathlib import Path

from .demo import approve_fixtures, seed, seed_gold
from .schemas import RunRequest
from .service import Workbench
from .storage import Store
from .worker import Worker


def main():
    parser = argparse.ArgumentParser(description="GovernLoom runtime governance and evaluation utilities")
    parser.add_argument("--db", help="SQLAlchemy SQLite URL; default sqlite:///data/governloom.db")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="Accept repository fixtures, freeze dataset, evaluate clean and five faulty targets")
    bootstrap = commands.add_parser("bootstrap-admin", help="Create the first named administrator (password prompted privately)")
    bootstrap.add_argument("username")
    bootstrap.add_argument("--password-stdin", action="store_true", help="Read one password line from stdin for automation")
    worker_parser = commands.add_parser("worker", help="Run the durable background worker")
    worker_parser.add_argument("--once", action="store_true")
    webhook_parser = commands.add_parser("webhook-worker", help="Deliver signed incidents to registered, host-allowed destinations")
    webhook_parser.add_argument("--once", action="store_true")
    monitor_parser = commands.add_parser("monitor-worker", help="Persist alerts for explicit missing numeric outcome deadlines")
    monitor_parser.add_argument("--once", action="store_true")
    export = commands.add_parser("export", help="Export versioned records as UTF-8 JSONL")
    export.add_argument("kind", choices=["case", "source", "dataset", "trace_batch", "review_event", "run"])
    export.add_argument("path", type=Path)
    export.add_argument("--application-id")
    args = parser.parse_args()
    workbench = Workbench(Store(args.db))
    if args.command == "bootstrap-admin":
        import getpass
        import sys
        from .auth import Operators, UserCreate
        password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else getpass.getpass("New administrator password (15+ characters): ")
        record = Operators(workbench).create(UserCreate(username=args.username, password=password, role="admin"), "local-bootstrap", bootstrap=True)
        print(f"Created administrator {record['username']}. Start with GOVERNLOOM_AUTH_MODE=operators.")
    elif args.command == "monitor-worker":
        import time
        from .monitoring import Monitor
        from .outcomes import Outcomes
        outcomes = Outcomes(Monitor(workbench))
        if args.once:
            print(json.dumps(outcomes.sweep()))
        else:
            print("GovernLoom outcome monitor ready", flush=True)
            try:
                while True:
                    outcomes.sweep()
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    elif args.command == "webhook-worker":
        import time
        from .webhooks import Webhooks
        notifications = Webhooks(workbench)
        if args.once:
            print(json.dumps(notifications.dispatch()))
        else:
            print("GovernLoom webhook worker ready", flush=True)
            try:
                while True:
                    notifications.dispatch()
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass
    elif args.command == "worker":
        worker = Worker(workbench.store)
        print("GovernLoom worker ready", flush=True)
        worker.run_once() if args.once else worker.serve()
    elif args.command == "export":
        rows = workbench.runs(args.application_id) if args.kind == "run" else workbench.store.list(args.kind, args.application_id)
        if args.kind == "run":
            rows = [workbench.run(r["id"]) for r in rows]
        args.path.parent.mkdir(parents=True, exist_ok=True)
        args.path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        print(f"Exported {len(rows)} {args.kind} records to {args.path}")
    else:
        application = seed(workbench)
        seed_gold(workbench, application["id"])
        approve_fixtures(workbench, application["id"])
        dataset = workbench.publish(application["id"], "demo-script (fixture acceptance, not human review)")
        print(f"Frozen dataset {dataset['id']}: {len(dataset['cases'])} cases; checksum {dataset['checksum']}")
        run_ids = []
        for target in ("clean", "irrelevant_retrieval", "outdated_source", "unsupported_statement", "invalid_citation", "timeout"):
            run = workbench.queue(RunRequest(dataset_id=dataset["id"], target=target, split="held_out"))
            run_ids.append(run["id"])
            while workbench.run(run["id"])["status"] in ("queued", "running"):
                if not Worker(workbench.store).run_once():
                    raise RuntimeError("Demo worker could not claim its queued run")
            run = workbench.run(run["id"])
            failed = sum(any(m["status"] == "failed" for m in r["metrics"]) for r in run["results"])
            print(f"{target}: {run['status']}; {failed}/{run['total']} cases with deterministic findings; {run['id']}")
            if run["status"] != "completed":
                raise RuntimeError(run["error"] or "Run did not complete")
        comparison = workbench.compare(run_ids[0], run_ids[4])
        print(json.dumps({"comparison": {"compatible": comparison["compatible"], "matched_cases": comparison["matched_cases"],
              "measurement_changes": len(comparison["changes"]), "reasons": comparison["reasons"]}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
