"""Local test-only sink with stable-ID acknowledgment and injected retry failure."""

import os

from fastapi import Request
from fastapi.responses import JSONResponse

from examples.common import State, service


def create_app():
    api = service("GovernLoom test sink")
    state = State("test-sink")

    @api.get("/governloom-test-sink")
    def identity():
        return {"service": "governloom-test-sink", "schema_version": 1}

    @api.post("/governloom-test-sink")
    async def receive(request: Request):
        if request.headers.get("authorization"):
            return JSONResponse({"detail": "Never send account credentials to the test sink"}, status_code=400)
        body = await request.json()
        identifier = body.get("id")
        if not isinstance(identifier, str) or len(identifier) > 128:
            return JSONResponse({"detail": "Invalid notification ID"}, status_code=400)
        try:
            original = state.get(identifier)
            if original != body:
                return JSONResponse({"detail": "Conflicting notification"}, status_code=409)
        except ValueError:
            state.put(identifier, "notification", body)
            if os.environ.get("SINK_LOSE_FIRST_ACK") == "1":
                return JSONResponse({"detail": "Declared lost acknowledgment"}, status_code=503)
        return {"accepted_id": identifier}

    @api.get("/notifications")
    def notifications():
        return state.list("notification")

    return api
