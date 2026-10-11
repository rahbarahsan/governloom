from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from governloom.recovery import backup_bundle, delivery_retention, restore_bundle
from governloom.service import Workbench
from governloom.storage import Entity, Store
from governloom.webhooks import SecretRotation, Webhooks, verify_webhook
from test_webhooks import setup


def test_full_restore_pending_delivery_rotation_and_tamper(workbench, tmp_path):
    app, original, destination, monitor, key, event, receipt = setup(workbench, tmp_path)
    rotated = original.rotate(destination["id"], SecretRotation(actor="operator", expected_revision=1))
    bundle, recovered = tmp_path / "bundle", tmp_path / "recovered"
    record = backup_bundle(workbench.store.url.removeprefix("sqlite:///"), original.secrets_directory, bundle)
    assert record["secret_files"] == 2
    assert restore_bundle(bundle, recovered)["secret_files"] == 2
    store = Store(f"sqlite:///{(recovered / 'collector.db').as_posix()}")
    def receiver(endpoint, body, headers, *rest):
        verify_webhook(rotated["secret"], headers, body)
        verify_webhook(destination["secret"], headers, body)
        return 204, None
    try:
        hooks = Webhooks(Workbench(store), allowed=original.allowed, secrets_directory=recovered / "secrets", transport=receiver)
        assert hooks.dispatch()["delivered"] == 1
    finally:
        store.engine.dispose()
    with pytest.raises(FileExistsError):
        restore_bundle(bundle, recovered)
    secret = next((bundle / "secrets").iterdir())
    secret.write_text("tampered", encoding="ascii")
    with pytest.raises(ValueError, match="checksum"):
        restore_bundle(bundle, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


def test_retention_protects_dead_letters_live_incident_and_all_audit(workbench, tmp_path):
    app, hooks, _, monitor, _, _, _ = setup(workbench, tmp_path, lambda *args: (204, None))
    hooks.dispatch()
    path = workbench.store.url.removeprefix("sqlite:///")
    with workbench.store.session() as session:
        row = session.scalar(select(Entity).where(Entity.kind == "webhook_delivery"))
        row.payload = {**row.payload, "updated_at": (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()}
    assert delivery_retention(path, 30, "operator")["eligible_deliveries"] == 0
    with workbench.store.session() as session:
        row = session.scalar(select(Entity).where(Entity.kind == "runtime_incident"))
        row.payload = {**row.payload, "status": "mitigated"}
    audits_before = len(workbench.store.list("review_event"))
    assert delivery_retention(path, 30, "operator")["eligible_deliveries"] == 1
    assert hooks.deliveries(app["id"])
    assert delivery_retention(path, 30, "operator", apply=True)["eligible_deliveries"] == 1
    assert not hooks.deliveries(app["id"])
    assert len(workbench.store.list("review_event")) == audits_before + 1
    assert monitor.alerts(app["id"])
