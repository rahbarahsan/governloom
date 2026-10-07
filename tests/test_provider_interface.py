import pytest

from governloom.demo import generate_candidates, seed
from governloom.providers import ProviderSession
from governloom.schemas import ProviderConfig


class FakeProvider:
    def __init__(self, fail=False, invalid=False):
        self.calls = 0
        self.fail = fail
        self.invalid = invalid

    def generate(self, sources, config):
        self.calls += 1
        if self.fail:
            raise TimeoutError("Fake provider deadline")
        case = generate_candidates(sources[0]["application_id"], sources)[0].model_dump()
        if self.invalid:
            case["references"][0]["quote"] = "invented evidence"
        return [case]

    def judge(self, case, trace, rubric, config):
        self.calls += 1
        return {"judge": "deterministic integration fake", "model_version": config.model_version,
                "rubric_version": rubric, "score": 0.5, "explanation": "Integration test only",
                "evidence": case["references"], "calibration": "adapter claims calibrated"}


def test_fake_provider_grounded_import_and_estimate(workbench):
    app = seed(workbench)
    source = next(s for s in workbench.store.list("source", app["id"]) if s["version"] == "v2")
    adapter = FakeProvider()
    session = ProviderSession(ProviderConfig(enabled=True, spending_cap=0.02, max_requests=2, model_version="fake-v1"), adapter)
    cases = session.candidates(workbench, app["id"], [source["id"]], 0.01)
    assert cases[0]["review_status"] == "unreviewed" and "model-generated estimate" in cases[0]["provenance"]
    estimate = session.estimate(workbench, cases[0], {}, "rubric-v1", 0.01)
    assert estimate["score"] == 0.5 and estimate["calibration"].startswith("unavailable")
    with pytest.raises(ValueError, match="limit"):
        session.candidates(workbench, app["id"], [source["id"]], 0.01)
    assert adapter.calls == 2


@pytest.mark.parametrize("failure", ["timeout", "invalid_evidence"])
def test_fake_provider_failures_do_not_publish_or_retry(workbench, failure):
    app = seed(workbench)
    source = workbench.store.list("source", app["id"])[0]
    adapter = FakeProvider(fail=failure == "timeout", invalid=failure == "invalid_evidence")
    session = ProviderSession(ProviderConfig(enabled=True, spending_cap=0.01, max_requests=1, model_version="fake-v1"), adapter)
    with pytest.raises((TimeoutError, ValueError)):
        session.candidates(workbench, app["id"], [source["id"]], 0.01)
    assert workbench.store.list("case", app["id"]) == []
    assert adapter.calls == 1 and session.budget.requests == 1 and session.budget.reserved == 0.01
