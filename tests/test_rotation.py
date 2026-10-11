import json
import time

import pytest

from governloom.webhooks import SecretRotation, verify_webhook
from test_webhooks import setup, due


def test_overlap_new_old_expiry_emergency_and_no_secret_leaks(workbench, tmp_path):
    captured = []
    app, hooks, original, monitor, key, event, receipt = setup(workbench, tmp_path,
        lambda endpoint, body, headers, *args: (captured.append((body, headers)) or (503, None)))
    rotated = hooks.rotate(original["id"], SecretRotation(actor="operator", expected_revision=1, overlap_seconds=60))
    assert rotated["secret"] != original["secret"] and rotated["revision"] == 2
    hooks.dispatch()
    body, headers = captured[-1]
    assert len(headers["webhook-signature"].split()) == 2
    verify_webhook(original["secret"], headers, body)
    verify_webhook(rotated["secret"], headers, body)
    with pytest.raises(ValueError, match="overlap"):
        hooks.rotate(original["id"], SecretRotation(actor="operator", expected_revision=2))
    delivery = hooks.deliveries(app["id"])[0]
    with workbench.store.session() as session:
        from governloom.storage import Entity
        row = session.get(Entity, original["id"])
        row.payload = {**row.payload, "previous_secret_until": time.time() - 1}
    due(hooks, delivery["id"])
    hooks.dispatch()
    body, headers = captured[-1]
    assert len(headers["webhook-signature"].split()) == 1
    verify_webhook(rotated["secret"], headers, body)
    with pytest.raises(ValueError):
        verify_webhook(original["secret"], headers, body)
    emergency = hooks.rotate(original["id"], SecretRotation(actor="operator", expected_revision=2, overlap_seconds=0))
    due(hooks, delivery["id"])
    hooks.dispatch()
    body, headers = captured[-1]
    verify_webhook(emergency["secret"], headers, body)
    with pytest.raises(ValueError):
        verify_webhook(rotated["secret"], headers, body)
    public = json.dumps(hooks.destinations(app["id"]) + hooks.deliveries(app["id"]) + workbench.store.list("review_event", app["id"]))
    for secret in (original["secret"], rotated["secret"], emergency["secret"]):
        assert secret not in public
    assert "secret_ref" not in public
