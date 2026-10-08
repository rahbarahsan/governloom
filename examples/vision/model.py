import importlib.metadata

import numpy as np
from sklearn.datasets import load_digits
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from examples.common import digest


class DigitModel:
    def __init__(self):
        dataset = load_digits()
        self.images, self.labels = dataset.data, dataset.target
        indices = np.arange(len(self.labels))
        train, other = train_test_split(indices, test_size=0.35, stratify=self.labels, random_state=41)
        calibration, held_out = train_test_split(other, test_size=4 / 7, stratify=self.labels[other], random_state=42)
        self.train, self.calibration, self.held_out = map(lambda values: sorted(map(int, values)), (train, calibration, held_out))
        self.classifier = RandomForestClassifier(n_estimators=64, random_state=43, n_jobs=1).fit(
            self.images[self.train], self.labels[self.train])
        probabilities = self.classifier.predict_proba(self.images[self.calibration])
        # Select a 20% review budget on calibration only, then freeze it.
        self.threshold = float(np.quantile(probabilities.max(axis=1), 0.2))
        self.manifest = {
            "dataset": "UCI handwritten digits, sklearn bundled original-test subset",
            "dataset_url": "https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits",
            "attribution": "Alpaydin and Kaynak (1998), DOI 10.24432/C50P49, CC BY 4.0",
            "dataset_hash": digest(self.images.astype("<f8").tobytes() + self.labels.astype("<i8").tobytes()),
            "splits": {name: {"count": len(values), "index_hash": digest(values)} for name, values in
                       (("train", self.train), ("calibration", self.calibration), ("held_out", self.held_out))},
            "algorithm": "RandomForestClassifier", "trees": 64, "model_seed": 43,
            "sklearn_version": importlib.metadata.version("scikit-learn"), "numpy_version": np.__version__,
            "confidence_threshold": self.threshold, "selection": "20th confidence percentile on calibration only",
        }
        self.version = "digits-rf-" + digest(self.manifest)[:16]
        self.manifest["model_version"] = self.version

    def sample(self, identifier, corruption="none"):
        if identifier not in self.held_out:
            raise ValueError("Sample must belong to the frozen held-out partition")
        pixels = self.images[identifier].copy().reshape(8, 8)
        if corruption == "occlusion":
            pixels[:, 2:6] = 0
        elif corruption == "noise":
            pixels = np.random.default_rng(identifier + 1000).integers(0, 17, (8, 8)).astype(float)
        elif corruption != "none":
            raise ValueError("Unknown corruption")
        return pixels.ravel().tolist()

    def predict(self, pixels):
        probabilities = self.classifier.predict_proba(np.asarray(pixels, dtype=float).reshape(1, 64))[0]
        return {"prediction": int(self.classifier.classes_[probabilities.argmax()]),
                "confidence": float(probabilities.max())}

    def evaluate(self):
        rows = []
        for identifier in self.held_out:
            output = self.predict(self.images[identifier])
            rows.append({"sample_id": identifier, **output, "actual": int(self.labels[identifier]),
                         "review": output["confidence"] < self.threshold})
        errors = [row for row in rows if row["prediction"] != row["actual"]]
        return {"cases": len(rows), "correct": len(rows) - len(errors), "errors": len(errors),
                "review_count": sum(row["review"] for row in rows), "errors_flagged": sum(row["review"] for row in errors),
                "confident_errors_missed": sum(not row["review"] for row in errors), "rows": rows}
