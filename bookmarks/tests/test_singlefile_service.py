import signal
import subprocess
from unittest.mock import patch, MagicMock, call
from django.test import SimpleTestCase, override_settings
from bookmarks.services.singlefile import create_snapshot, SingleFileError


class SingleFileServiceBlackBoxTestCase(SimpleTestCase):

    @patch("bookmarks.services.singlefile.os.path.exists", return_value=True)
    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_create_snapshot_success(self, mock_popen, mock_exists):
        """CP-01: Caminho feliz - processo encerra com sucesso e arquivo existe."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        create_snapshot("https://example.com", "/tmp/test.html")

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
        # Primeiro wait estoura o timeout, segundo wait (na terminação) encerra normalmente
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="single-file", timeout=30),
            None
        ]
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


class SingleFileServiceWhiteBoxTestCase(SimpleTestCase):
    """
    Testes de Caixa-Branca para a função create_snapshot.
    Foca em ramos internos, tratamento de sinais, níveis de timeout e exceções.
    """

    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_timeout_level_1_graceful_termination(self, mock_popen):
        """CB-01: Primeiro timeout aciona terminate() e wait(timeout=20) com sucesso."""
        mock_process = MagicMock()
        mock_pid = 12345
        mock_process.pid = mock_pid
        
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="single-file", timeout=30),
            None 
        ]
        mock_popen.return_value = mock_process

        with patch("bookmarks.services.singlefile.os.killpg") as mock_killpg:
            with self.assertRaises(SingleFileError) as ctx:
                create_snapshot("https://example.com", "/tmp/test.html")

            self.assertEqual(str(ctx.exception), "Timeout expired while creating snapshot")
            mock_process.terminate.assert_called_once()
            mock_killpg.assert_not_called()

    @patch("bookmarks.services.singlefile.os.getpgid")
    @patch("bookmarks.services.singlefile.os.killpg")
    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_timeout_level_2_force_kill(self, mock_popen, mock_killpg, mock_getpgid):
        """CB-02: Timeout persistente aciona getpgid e killpg com SIGTERM."""
        mock_process = MagicMock()
        mock_pid = 9999
        mock_pgid = 9998
        mock_process.pid = mock_pid
        mock_getpgid.return_value = mock_pgid

        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="single-file", timeout=30),
            subprocess.TimeoutExpired(cmd="single-file", timeout=20)
        ]
        mock_popen.return_value = mock_process

        with self.assertRaises(SingleFileError) as ctx:
            create_snapshot("https://example.com", "/tmp/test.html")

        self.assertEqual(str(ctx.exception), "Timeout expired while creating snapshot")
        mock_process.terminate.assert_called_once()
        mock_getpgid.assert_called_once_with(mock_pid)
        mock_killpg.assert_called_once_with(mock_pgid, signal.SIGTERM)

    @patch("bookmarks.services.singlefile.os.path.exists", return_value=True)
    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_start_new_session_parameter(self, mock_popen, mock_exists):
        """CB-03: Assegura que Popen é invocado com start_new_session=True."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        create_snapshot("https://example.com", "/tmp/test.html")

        _, kwargs = mock_popen.call_args
        self.assertTrue(kwargs.get("start_new_session"))

    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_exception_chaining_and_suppression(self, mock_popen):
        """CB-04: Valida o encadeamento correto em CalledProcessError e supressão em Timeout."""
        mock_process = MagicMock()
        called_error = subprocess.CalledProcessError(returncode=2, cmd="single-file", stderr=b"err")
        mock_process.wait.side_effect = called_error
        mock_popen.return_value = mock_process
        with self.assertRaises(SingleFileError) as ctx:
            create_snapshot("https://example.com", "/tmp/test.html")
        self.assertEqual(ctx.exception.__cause__, called_error)

        # Verifica supressão de contexto (__suppress_context__ = True) nos timeouts
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="single-file", timeout=30),
            None
        ]
        with self.assertRaises(SingleFileError) as ctx_timeout:
            create_snapshot("https://example.com", "/tmp/test.html")
        self.assertTrue(ctx_timeout.exception.__suppress_context__)

    @patch("bookmarks.services.singlefile.os.getpgid")
    @patch("bookmarks.services.singlefile.os.killpg")
    @patch("bookmarks.services.singlefile.subprocess.Popen")
    def test_timeout_error_logging_calls(self, mock_popen, mock_killpg, mock_getpgid):
        """CB-05: Valida que mensagens de erro de logger são emitidas em cada nível de timeout."""
        mock_process = MagicMock()
        mock_pid = 7777
        mock_pgid = 7770
        mock_process.pid = mock_pid
        mock_getpgid.return_value = mock_pgid
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="single-file", timeout=30),
            subprocess.TimeoutExpired(cmd="single-file", timeout=20)
        ]
        mock_popen.return_value = mock_process

        with patch("bookmarks.services.singlefile.logger") as mock_logger:
            with self.assertRaises(SingleFileError):
                create_snapshot("https://example.com", "/tmp/test.html")

            expected_logs = [
                call("Timeout expired while creating snapshot. Terminating process..."),
                call("Timeout expired while terminating. Killing process...")
            ]
            mock_logger.error.assert_has_calls(expected_logs, any_order=False)
