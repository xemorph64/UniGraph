from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "ingestion" / "debezium" / "mock-cbs-generator.py"


def _load_generator_module():
    spec = importlib.util.spec_from_file_location("mock_cbs_generator", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load mock-cbs-generator module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MockCBSGeneratorTests(unittest.TestCase):
    def test_normal_generation_count_and_shape(self):
        module = _load_generator_module()
        events = module.generate_normal_transactions(10)

        self.assertEqual(len(events), 10)
        self.assertIn("after", events[0])
        self.assertIn("from_account", events[0]["after"])
        self.assertIn("to_account", events[0]["after"])
        self.assertIn("amount", events[0]["after"])

    def test_mixed_builder_contains_events(self):
        module = _load_generator_module()
        events = module._build_events("mixed", 20)

        self.assertGreaterEqual(len(events), 20)
        fraud_like = [evt for evt in events if evt.get("after", {}).get("amount", 0) >= 50000]
        self.assertTrue(fraud_like)

    def test_cli_writes_jsonl_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "mock-events.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--scenario",
                    "normal",
                    "--count",
                    "7",
                    "--output",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["events_generated"], 7)
            self.assertTrue(output_path.exists())

            lines = output_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 7)
            for line in lines:
                decoded = json.loads(line)
                self.assertIn("after", decoded)


if __name__ == "__main__":
    unittest.main()
