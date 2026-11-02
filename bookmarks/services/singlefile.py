import logging
import os
import shlex
import signal
import subprocess

from django.conf import settings

from bookmarks.services import ssrf_proxy


class SingleFileError(Exception):
    pass


logger = logging.getLogger(__name__)


def create_snapshot(url: str, filepath: str):
    singlefile_path = settings.LD_SINGLEFILE_PATH

    # parse options to list of arguments
    ublock_options = shlex.split(settings.LD_SINGLEFILE_UBLOCK_OPTIONS)
    custom_options = shlex.split(settings.LD_SINGLEFILE_OPTIONS)
    # Run the snapshot browser behind the egress proxy, so every request it
    # makes — page, redirect hop, subresource — goes through the same SSRF
    # policy as the pre-check, instead of the browser's own network stack.
    # Proxy args come last so they win over any admin-set proxy option, and
    # <-loopback> stops Chromium from bypassing the proxy for local targets.
    with ssrf_proxy.egress_proxy() as proxy_port:
        proxy_options = [
            f'--browser-arg="--proxy-server=http://127.0.0.1:{proxy_port}"',
            '--browser-arg="--proxy-bypass-list=<-loopback>"',
        ]
        args = (
            [singlefile_path]
            + ublock_options
            + custom_options
            + proxy_options
            + [url, filepath]
        )
        _run_singlefile(args, filepath)


def _run_singlefile(args: list[str], filepath: str):
    try:
        # Use start_new_session=True to create a new process group
        process = subprocess.Popen(args, start_new_session=True)
        process.wait(timeout=settings.LD_SINGLEFILE_TIMEOUT_SEC)

        # check if the file was created
        if not os.path.exists(filepath):
            raise SingleFileError("Failed to create snapshot")
    except subprocess.TimeoutExpired:
        # First try to terminate properly
        try:
            logger.error(
                "Timeout expired while creating snapshot. Terminating process..."
            )
            process.terminate()
            process.wait(timeout=20)
            raise SingleFileError("Timeout expired while creating snapshot") from None
        except subprocess.TimeoutExpired:
            # Kill the whole process group, which should also clean up any chromium
            # processes spawned by single-file
            logger.error("Timeout expired while terminating. Killing process...")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            raise SingleFileError("Timeout expired while creating snapshot") from None
    except subprocess.CalledProcessError as error:
        raise SingleFileError(f"Failed to create snapshot: {error.stderr}") from error
