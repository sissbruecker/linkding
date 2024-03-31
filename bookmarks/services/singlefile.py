import gzip
import os
import shutil
import subprocess

from django.conf import settings


class SingeFileError(Exception):
    pass


def create_snapshot(url: str, filepath: str):
    singlefile_path = settings.LD_SINGLEFILE_PATH
    singlefile_options = settings.LD_SINGLEFILE_OPTIONS
    temp_filepath = filepath + ".tmp"

    try:
        command = f"{singlefile_path} '{url}' {singlefile_options} {temp_filepath}"
        subprocess.run(command, check=True, shell=True)

        # single-file doesn't return exit codes apparently, so check if the file was created
        if not os.path.exists(temp_filepath):
            raise SingeFileError("Failed to create snapshot")

        with open(temp_filepath, "rb") as raw_file, gzip.open(
            filepath, "wb"
        ) as gz_file:
            shutil.copyfileobj(raw_file, gz_file)

        os.remove(temp_filepath)
    except subprocess.CalledProcessError as error:
        raise SingeFileError(f"Failed to create snapshot: {error.stderr}")
