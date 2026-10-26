import signal
import subprocess
from unittest.mock import patch, MagicMock, call
from django.test import SimpleTestCase, override_settings
from bookmarks.services.singlefile import create_snapshot, SingleFileError


class SingleFileServiceBlackBoxTestCase(SimpleTestCase):
    """
    Testes de Caixa-Preta para a função create_snapshot.
    Foca em entradas, saídas, contratos e comportamentos externos observáveis.
    """

    @patch("bookmarks.services.singlefile.os.path.exists", return_value=True)
    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_create_snapshot_success(self, mock_popen, mock_exists):
        """CP-01: Caminho feliz - processo encerra com sucesso e arquivo existe."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        # Execução
        create_snapshot("https://example.com", "/tmp/test.html")

        # Asserções de contrato
        mock_popen.assert_called_once()
        mock_process.wait.assert_called_once()
        mock_exists.assert_called_once_with("/tmp/test.html")

    @patch("bookmarks.services.singlefile.os.path.exists", return_value=False)
    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_create_snapshot_file_not_created(self, mock_popen, mock_exists):
        """CP-02: Processo termina mas o arquivo não é encontrado no disco."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        with self.assertRaises(SingleFileError) as ctx:
            create_snapshot("https://example.com", "/tmp/test.html")

        self.assertEqual(str(ctx.exception), "Failed to create snapshot")

    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_create_snapshot_called_process_error(self, mock_popen):
        """CP-03: Subprocess falha com CalledProcessError."""
        mock_process = MagicMock()
        error = subprocess.CalledProcessError(returncode=1, cmd="single-file", stderr=b"CLI error")
        mock_process.wait.side_effect = error
        mock_popen.return_value = mock_process

        with self.assertRaises(SingleFileError) as ctx:
            create_snapshot("https://example.com", "/tmp/test.html")

        self.assertIn("Failed to create snapshot: b'CLI error'", str(ctx.exception))

    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_create_snapshot_timeout_general(self, mock_popen):
        """CP-04: Timeout geral resulta em SingleFileError padronizado."""
        mock_process = MagicMock()
        # Força TimeoutExpired em todas as esperas para esgotar a recuperação
        mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="single-file", timeout=30)
        mock_popen.return_value = mock_process

        with self.assertRaises(SingleFileError) as ctx:
            create_snapshot("https://example.com", "/tmp/test.html")

        self.assertEqual(str(ctx.exception), "Timeout expired while creating snapshot")

    @override_settings(
        LD_SINGLEFILE_PATH="/usr/bin/single-file",
        LD_SINGLEFILE_OPTIONS="--browser-option no-sandbox",
        LD_SINGLEFILE_UBLOCK_OPTIONS="--disable-extensions",
        LD_SINGLEFILE_TIMEOUT_SEC=45
    )
    @patch("bookmarks.services.singlefile.os.path.exists", return_value=True)
    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_create_snapshot_custom_settings(self, mock_popen, mock_exists):
        """CP-05: Respeita as configurações customizadas do Django settings."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        create_snapshot("https://example.com", "/tmp/test.html")

        # Verifica se os argumentos refletem os settings injetados
        expected_args = [
            "/usr/bin/single-file",
            "--disable-extensions",
            "--browser-option",
            "no-sandbox",
            "https://example.com",
            "/tmp/test.html"
        ]
        mock_popen.assert_called_once_with(expected_args, start_new_session=True)
        mock_process.wait.assert_called_once_with(timeout=45)
