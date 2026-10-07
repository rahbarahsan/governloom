import pytest

from governloom.demo import approve_fixtures, seed, seed_gold
from governloom.service import Workbench
from governloom.storage import Store


@pytest.fixture
def workbench(tmp_path):
    return Workbench(Store(f"sqlite:///{(tmp_path / 'test.db').as_posix()}"))


@pytest.fixture
def demo(workbench):
    app = seed(workbench)
    seed_gold(workbench, app["id"])
    approve_fixtures(workbench, app["id"])
    dataset = workbench.publish(app["id"], "test fixture acceptance")
    return workbench, app, dataset
