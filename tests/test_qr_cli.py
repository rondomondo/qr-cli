"""
tests/test_qr_cli.py
~~~~~~~~~~~~~~~~~~~~
Basic tests for qr-cli.

Run with: pytest tests/ -v
"""

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class TestDockerBackend(unittest.TestCase):

    def test_unavailable_when_no_docker_binary(self):
        from qr_cli.backends import DockerBackend
        b = DockerBackend()
        with patch("shutil.which", return_value=None):
            self.assertFalse(b.available())

    def test_unavailable_when_docker_info_fails(self):
        from qr_cli.backends import DockerBackend
        import subprocess
        b = DockerBackend()
        with patch("shutil.which", return_value="/usr/bin/docker"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                self.assertFalse(b.available())

    def test_run_parses_json(self):
        from qr_cli.backends import DockerBackend
        payload = json.dumps({"success": True, "meta": {}, "image": {"base64": "abc"}})
        b = DockerBackend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=payload)
            result = b.run(["--data=https://example.com"])
        self.assertTrue(result["success"])

    def test_run_returns_error_on_bad_json(self):
        from qr_cli.backends import DockerBackend
        b = DockerBackend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not json")
            result = b.run(["--data=https://example.com"])
        self.assertFalse(result["success"])
        self.assertIn("JSON", result["error"])


class TestNodeBackend(unittest.TestCase):

    def test_unavailable_when_no_node(self):
        from qr_cli.backends import NodeBackend
        b = NodeBackend()
        with patch("shutil.which", return_value=None):
            self.assertFalse(b.available())

    def test_modules_installed_check(self):
        from qr_cli.backends import NodeBackend
        with tempfile.TemporaryDirectory() as td:
            b = NodeBackend(node_dir=td)
            self.assertFalse(b._modules_installed())
            os.makedirs(os.path.join(td, "node_modules"))
            self.assertTrue(b._modules_installed())

    def test_run_parses_json(self):
        from qr_cli.backends import NodeBackend
        payload = json.dumps({"success": True, "meta": {}, "image": {"base64": "abc"}})
        b = NodeBackend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=payload)
            result = b.run(["--data=https://example.com"])
        self.assertTrue(result["success"])


class TestGetBackend(unittest.TestCase):

    def test_prefers_docker_when_available(self):
        from qr_cli import backends
        with patch.object(backends.DockerBackend, "available", return_value=True):
            b = backends.get_backend()
        self.assertEqual(b.name, "docker")

    def test_falls_back_to_node_when_no_docker(self):
        from qr_cli import backends
        with patch.object(backends.DockerBackend, "available", return_value=False):
            with patch.object(backends.NodeBackend, "ensure_installed"):
                b = backends.get_backend()
        self.assertEqual(b.name, "node")

    def test_force_node_backend(self):
        from qr_cli import backends
        with patch.object(backends.NodeBackend, "ensure_installed"):
            b = backends.get_backend(prefer="node")
        self.assertEqual(b.name, "node")

    def test_force_docker_falls_back_with_warning(self):
        import warnings
        from qr_cli import backends
        with patch.object(backends.DockerBackend, "available", return_value=False):
            with patch.object(backends.NodeBackend, "ensure_installed"):
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    b = backends.get_backend(prefer="docker")
        self.assertEqual(b.name, "node")
        self.assertTrue(any("Docker" in str(warning.message) for warning in w))


class TestGenerator(unittest.TestCase):

    def _mock_backend(self, success=True):
        mock = MagicMock()
        mock.name = "mock"
        payload = {
            "success": success,
            "meta": {"format": "png", "width": 300, "height": 300},
            "image": {
                "base64": "aGVsbG8=",  # base64("hello")
                "dataUri": "data:image/png;base64,aGVsbG8=",
                "filename": "qr.png",
            },
        }
        if not success:
            payload = {"success": False, "error": "test error"}
        mock.run.return_value = payload
        return mock

    def test_generate_returns_result(self):
        from qr_cli import generate
        mock = self._mock_backend()
        result = generate("https://example.com", backend=mock)
        self.assertTrue(result["success"])
        mock.run.assert_called_once()

    def test_generate_saves_file(self):
        from qr_cli import generate
        mock = self._mock_backend()
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "test.png")
            result = generate("https://example.com", backend=mock, save_to=out)
        self.assertIn("_saved_to", result)

    def test_generate_builds_correct_args(self):
        from qr_cli import generate
        mock = self._mock_backend()
        generate(
            "https://example.com",
            width=500, height=500,
            dots_color="#028f1e",
            bg_color="#ffb7ce",
            dots_type="rounded",
            error_correction="H",
            backend=mock,
        )
        args = mock.run.call_args[0][0]
        args_str = " ".join(args)
        self.assertIn("--data=https://example.com", args_str)
        self.assertIn("--width=500", args_str)
        self.assertIn("--dotsOptions.color=#028f1e", args_str)
        self.assertIn("--backgroundOptions.color=#ffb7ce", args_str)
        self.assertIn("--dotsOptions.type=rounded", args_str)
        self.assertIn("--qrOptions.errorCorrectionLevel=H", args_str)


if __name__ == "__main__":
    unittest.main()
