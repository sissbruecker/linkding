import gzip
import logging
import os
import shlex
import shutil
import signal
import subprocess

from django.conf import settings


class SingeFileError(Exception):
    pass


logger = logging.getLogger(__name__)


def create_snapshot(url: str, filepath: str):
    singlefile_path = settings.LD_SINGLEFILE_PATH
    # default options
    default_options = [
        '--browser-arg="--headless=new"',
        '--browser-arg="--no-sandbox"',
        '--browser-arg="--load-extension=uBlock0.chromium"',
        '--user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36"',
    ]
    # parse options to list of arguments
    singlefile_options = shlex.split(settings.LD_SINGLEFILE_OPTIONS)
    temp_filepath = filepath + ".tmp"
    # concat lists
    args = (
        [singlefile_path] + default_options + singlefile_options + [url, temp_filepath]
    )
    try:
        # Use start_new_session=True to create a new process group
        process = subprocess.Popen(args, start_new_session=True)
        process.wait(timeout=settings.LD_SINGLEFILE_TIMEOUT_SEC)

        # check if the file was created
        if not os.path.exists(temp_filepath):
            raise SingeFileError("Failed to create snapshot")

        with open(temp_filepath, "rb") as raw_file, gzip.open(
            filepath, "wb"
        ) as gz_file:
            shutil.copyfileobj(raw_file, gz_file)

        os.remove(temp_filepath)
    except subprocess.TimeoutExpired:
        # First try to terminate properly
        try:
            logger.error(
                "Timeout expired while creating snapshot. Terminating process..."
            )
            process.terminate()
            process.wait(timeout=20)
            raise SingeFileError("Timeout expired while creating snapshot")
        except subprocess.TimeoutExpired:
            # Kill the whole process group, which should also clean up any chromium
            # processes spawned by single-file
            logger.error("Timeout expired while terminating. Killing process...")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            raise SingeFileError("Timeout expired while creating snapshot")
    except subprocess.CalledProcessError as error:
        raise SingeFileError(f"Failed to create snapshot: {error.stderr}")
