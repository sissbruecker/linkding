import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.test import SimpleTestCase


def run_bash(command, env):
    return subprocess.run(
        ["bash", "-c", command],
        cwd=settings.BASE_DIR,
        env={"PATH": os.environ["PATH"], **env},
        capture_output=True,
        text=True,
        timeout=5,
    )


class LoadEnvFilesTestCase(SimpleTestCase):
    def test_file_values_override_environment_and_preserve_whitespace(self):
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "secret with spaces"
            secret_file.write_text(
                "  password $value `literal` $(literal)  \nsecond line\n\n"
            )

            result = run_bash(
                "source scripts/load-env-files.sh && load_env_files && "
                "printenv LD_NEW_OPTION OIDC_NEW_OPTION TZ HOST_NAME",
                env={
                    "LD_NEW_OPTION": "ordinary",
                    "LD_NEW_OPTION_FILE": str(secret_file),
                    "OIDC_NEW_OPTION_FILE": str(secret_file),
                    "TZ_FILE": str(secret_file),
                    "HOST_NAME_FILE": str(secret_file),
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "  password $value `literal` $(literal)  \nsecond line\n"
            "  password $value `literal` $(literal)  \nsecond line\n"
            "  password $value `literal` $(literal)  \nsecond line\n"
            "  password $value `literal` $(literal)  \nsecond line\n",
        )

    def test_empty_file_overrides_environment(self):
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "secret"
            secret_file.write_text("")

            result = run_bash(
                "source scripts/load-env-files.sh && load_env_files && "
                "printenv LD_DB_PASSWORD",
                env={
                    "LD_DB_PASSWORD": "ordinary",
                    "LD_DB_PASSWORD_FILE": str(secret_file),
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "\n")

    def test_ordinary_and_unrelated_variables_are_unchanged(self):
        result = run_bash(
            "source scripts/load-env-files.sh && load_env_files && "
            "printenv LD_DB_PASSWORD TZ SSL_CERT_FILE",
            env={
                "LD_DB_PASSWORD": "ordinary",
                "LD_DB_PASSWORD_FILE": "",
                "TZ": "America/Chicago",
                "SSL_CERT_FILE": "/missing/certificate.pem",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout, "ordinary\nAmerica/Chicago\n/missing/certificate.pem\n"
        )

    def test_unreadable_file_fails_without_falling_back_to_environment(self):
        with TemporaryDirectory() as directory:
            for path in (Path(directory) / "missing", Path(directory)):
                with self.subTest(path=path):
                    result = run_bash(
                        "source scripts/load-env-files.sh && load_env_files && "
                        "printenv LD_DB_PASSWORD",
                        env={
                            "LD_DB_PASSWORD": "ordinary-secret",
                            "LD_DB_PASSWORD_FILE": str(path),
                        },
                    )

                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("Could not read LD_DB_PASSWORD_FILE", result.stderr)
                    self.assertNotIn("ordinary-secret", result.stderr)

    def test_selected_variables_ignore_unrelated_files(self):
        with TemporaryDirectory() as directory:
            port_file = Path(directory) / "port"
            port_file.write_text("9190\n")
            context_file = Path(directory) / "context"
            context_file.write_text("private/\n")

            result = run_bash(
                "source scripts/load-env-files.sh && "
                "load_env_files LD_SERVER_PORT_FILE LD_CONTEXT_PATH_FILE && "
                "printenv LD_SERVER_PORT LD_CONTEXT_PATH",
                env={
                    "LD_SERVER_PORT_FILE": str(port_file),
                    "LD_CONTEXT_PATH_FILE": str(context_file),
                    "LD_SUPERUSER_PASSWORD_FILE": str(Path(directory) / "missing"),
                },
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "9190\nprivate/\n")
