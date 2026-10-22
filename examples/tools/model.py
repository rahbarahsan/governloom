"""A trained local intent classifier proposes tools; authorization is independent.

Small repository-authored training examples are an integration application, not a
benchmark for agent planning, malicious intent, or language generalization.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from governloom.service import checksum

TRAINING = [
    ("search documentation", "search"), ("find the documentation page", "search"),
    ("look up support information", "search"), ("search help articles", "search"),
    ("retrieve the manual", "search"), ("find instructions in the guide", "search"),
    ("delete my draft", "delete_draft"), ("remove this draft permanently", "delete_draft"),
    ("delete the stored draft", "delete_draft"), ("erase my draft", "delete_draft"),
    ("remove the saved draft", "delete_draft"), ("erase the draft permanently", "delete_draft"),
]
REQUESTS = ["search the guide", "delete the draft", "find support articles", "erase the saved draft",
            "look up documentation", "remove my draft", "retrieve help information", "delete my saved draft"]


class ToolPlanner:
    def __init__(self):
        self.model = make_pipeline(TfidfVectorizer(), LogisticRegression(random_state=73)).fit(
            [text for text, _ in TRAINING], [label for _, label in TRAINING])
        self.version = "intent-logistic-" + checksum(TRAINING)[:16]
        self.deleted = False

    def plan(self, request):
        return {"tool_name": str(self.model.predict([request])[0]), "model_version": self.version,
                "application_version": "owned-tools-v1", "environment": "owned-test"}

    def execute(self, proposed):
        # GovernLoom observes attempts. This independent application check is
        # responsible for preventing the example's deletion, even on collector loss.
        if proposed["tool_name"] != "search":
            raise PermissionError("The connected application's principal is read-only")
        return {"source_ids": ["local-manual"], "result": "Local documentation found"}


def observations():
    planner = ToolPlanner()
    rows = [{**planner.plan(request), "sample_id": index, "split": "calibration" if index < 4 else "held_out"}
            for index, request in enumerate(REQUESTS)]
    return rows, planner
