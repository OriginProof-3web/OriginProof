"""The supported container workflow does not require host Foundry."""

import subprocess
import unittest
from unittest.mock import patch

import env_check


class EnvironmentCheckTest(unittest.TestCase):
    def test_container_prerequisites(self):
        with (
            patch.object(env_check.Path, "is_file", return_value=True),
            patch.object(
                env_check.shutil,
                "which",
                side_effect=lambda name: None if name == "forge" else name,
            ),
            patch.object(env_check.subprocess, "run") as run,
        ):
            self.assertEqual(env_check.main(), 0)
            run.assert_called_once_with(
                ["docker", "compose", "version"], check=True, capture_output=True, timeout=10
            )
            run.side_effect = subprocess.CalledProcessError(1, "docker")
            self.assertEqual(env_check.main(), 1)
            run.side_effect = subprocess.TimeoutExpired("docker", 10)
            self.assertEqual(env_check.main(), 1)
            run.side_effect = OSError("missing")
            self.assertEqual(env_check.main(), 1)
        with patch.object(env_check.Path, "is_file", return_value=False):
            self.assertEqual(env_check.main(), 1)
        with (
            patch.object(env_check.Path, "is_file", return_value=True),
            patch.object(env_check.shutil, "which", return_value=None),
        ):
            self.assertEqual(env_check.main(), 1)
