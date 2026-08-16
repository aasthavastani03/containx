import json
import os
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTAINX = os.path.join(PROJECT_ROOT, "containx.py")


class TestContainX(unittest.TestCase):

    def run_containx(self, *args):
        return subprocess.run(
            [sys.executable, CONTAINX, *args],
            capture_output=True,
            text=True
        )

    def test_help(self):
        result = self.run_containx("--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("A Linux container runtime built from scratch", result.stdout)
        self.assertIn("run", result.stdout)
        self.assertIn("ps", result.stdout)
        self.assertIn("exec", result.stdout)

    def test_run_echo(self):
        result = self.run_containx("run", "echo", "test")

        self.assertEqual(result.returncode, 0)
        self.assertIn("Container ID:", result.stdout)
        self.assertIn("Container exited with code: 0", result.stdout)

    def test_run_creates_state(self):
        result = self.run_containx("run", "echo", "hello")

        self.assertEqual(result.returncode, 0)

        container_id = None

        for line in result.stdout.splitlines():
            if line.startswith("Container ID:"):
                container_id = line.split(":", 1)[1].strip()
                break

        self.assertIsNotNone(container_id)

        state_file = os.path.join(
            PROJECT_ROOT,
            "state",
            f"{container_id}.json"
        )

        self.assertTrue(os.path.exists(state_file))

        with open(state_file) as f:
            data = json.load(f)

        self.assertEqual(data["id"], container_id)
        self.assertEqual(data["status"], "exited")
        self.assertEqual(data["exit_code"], 0)

    def test_logs(self):
        result = self.run_containx("run", "echo", "ContainX test")

        self.assertEqual(result.returncode, 0)

        container_id = None

        for line in result.stdout.splitlines():
            if line.startswith("Container ID:"):
                container_id = line.split(":", 1)[1].strip()
                break

        self.assertIsNotNone(container_id)

        logs = self.run_containx("logs", container_id)

        self.assertEqual(logs.returncode, 0)
        self.assertIn("ContainX test", logs.stdout)

    def test_inspect(self):
        result = self.run_containx("run", "echo", "inspect test")

        self.assertEqual(result.returncode, 0)

        container_id = None

        for line in result.stdout.splitlines():
            if line.startswith("Container ID:"):
                container_id = line.split(":", 1)[1].strip()
                break

        self.assertIsNotNone(container_id)

        inspect = self.run_containx("inspect", container_id)

        self.assertEqual(inspect.returncode, 0)
        self.assertIn('"id"', inspect.stdout)
        self.assertIn('"status"', inspect.stdout)
        self.assertIn('"exit_code"', inspect.stdout)

    def test_missing_container(self):
        result = self.run_containx(
            "logs",
            "000000000000"
        )

        self.assertIn(
            "Logs not found",
            result.stdout
        )


if __name__ == "__main__":
    unittest.main()