from typing import Protocol

from .schemas import ProviderConfig


class CandidateProvider(Protocol):
    def generate(self, passages: list[dict], config: ProviderConfig) -> list[dict]: ...


class JudgeProvider(Protocol):
    def judge(self, case: dict, trace: dict, rubric: str, config: ProviderConfig) -> dict: ...


class UnavailableProvider:
    def generate(self, passages, config):
        raise ValueError("No provider adapter configured; no paid requests are supported in this release")

    def judge(self, case, trace, rubric, config):
        raise ValueError("No calibrated judge adapter configured")


class Budget:
    """Preflight reservation for future provider adapters; credentials remain server-side."""
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.requests = 0
        self.reserved = 0.0

    def reserve(self, maximum_cost: float):
        if not self.config.enabled or not self.config.model_version:
            raise ValueError("Provider is disabled or lacks a pinned model version")
        if self.config.spending_cap <= 0 or maximum_cost <= 0:
            raise ValueError("An explicit positive spending cap and request cost bound are required")
        if self.requests >= self.config.max_requests or self.reserved + maximum_cost > self.config.spending_cap:
            raise ValueError("Provider request/spending limit exceeded")
        self.requests += 1
        self.reserved += maximum_cost
