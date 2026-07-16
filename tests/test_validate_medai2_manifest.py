import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_medai2_manifest import validate_manifest  # noqa: E402


def row(patient: str, split: str, anatomy: str = "chest") -> dict:
    return {
        "image": f"{patient}.png",
        "patient_id": patient,
        "split": split,
        "anatomy": anatomy,
        "task": "classification",
        "answer": {
            "finding": "normal",
            "impression": "No acute finding.",
            "evidence": [],
        },
    }


class ManifestValidationTests(unittest.TestCase):
    def write_manifest(self, rows: list[dict]) -> Path:
        temporary = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        with temporary:
            for value in rows:
                temporary.write(json.dumps(value) + "\n")
        return Path(temporary.name)

    def test_valid_patient_separated_manifest(self) -> None:
        path = self.write_manifest(
            [row("train-a", "train"), row("val-a", "validation"), row("test-a", "test")]
        )
        self.assertTrue(validate_manifest(path, require_test=True)["passed"])

    def test_patient_leakage_fails(self) -> None:
        path = self.write_manifest(
            [row("same", "train"), row("same", "validation"), row("test-a", "test")]
        )
        report = validate_manifest(path, require_test=True)
        self.assertFalse(report["passed"])
        self.assertTrue(any("patient leakage" in value for value in report["errors"]))

    def test_training_confidence_fails(self) -> None:
        record = row("train-a", "train")
        record["answer"]["confidence"] = 0.99
        path = self.write_manifest([record, row("val-a", "validation"), row("test-a", "test")])
        report = validate_manifest(path, require_test=True)
        self.assertFalse(report["passed"])
        self.assertTrue(any("self-reported confidence" in value for value in report["errors"]))


if __name__ == "__main__":
    unittest.main()
