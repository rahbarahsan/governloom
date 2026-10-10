"""Freeze version-one event bodies before retries or batch admission."""
from .monitoring import RuntimeEvent


def prepare_event(**fields):
    return RuntimeEvent(**fields).model_dump(mode="json")
