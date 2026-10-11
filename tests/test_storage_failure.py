import sqlite3

import pytest
from sqlalchemy.exc import OperationalError

from governloom.monitoring import RuntimeEvent
from test_outcomes import provision


def test_actual_sqlite_full_rolls_back_and_exact_event_can_recover(workbench):
    app, monitor, key, context, _ = provision(workbench)
    # A SQLite page cap creates the actual SQLITE_FULL failure without filling
    # the user's disk. Keep the same pooled connection and lift the cap afterward.
    with workbench.store.session() as session:
        pages = session.connection().exec_driver_sql("PRAGMA page_count").scalar()
        session.connection().exec_driver_sql(f"PRAGMA max_page_count={pages}")
    event = RuntimeEvent(**context, phase="output", labels=[f"opaque-label-{i:03d}-" + "x" * 175 for i in range(100)], metrics={"prediction": 1})
    try:
        with pytest.raises(OperationalError) as failed:
            monitor.ingest(key, event)
        assert failed.value.orig.sqlite_errorcode == sqlite3.SQLITE_FULL
        assert monitor.events(app["id"])["events"] == []
        assert not monitor.alerts(app["id"])
    finally:
        with workbench.store.session() as session:
            session.connection().exec_driver_sql("PRAGMA max_page_count=2147483646")
    accepted = monitor.ingest(key, event)
    assert not accepted["duplicate"] and monitor.ingest(key, event)["duplicate"]
