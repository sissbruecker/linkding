import gzip
import shutil
import subprocess
import os

from django.conf import settings


class MonolithError(Exception):
    pass


# Monolith isn't used at the moment, as the local snapshot implementation
# switched to single-file after the prototype. Keeping this around in case
# it turns out to be useful in the future.
def create_snapshot(url: str, filepath: str):
    monolith_path = settings.LD_MONOLITH_PATH
    monolith_options = settings.LD_MONOLITH_OPTIONS
    temp_filepath = filepath + ".tmp"

    try:
        command = f"{monolith_path} '{url}' {monolith_options} -o {temp_filepath}"
        subprocess.run(command, check=True, shell=True)

        with open(temp_filepath, "rb") as raw_file, gzip.open(
            filepath, "wb"
        ) as gz_file:
            shutil.copyfileobj(raw_file, gz_file)

        os.remove(temp_filepath)
    except subprocess.CalledProcessError as error:
        raise MonolithError(f"Failed to create snapshot: {error.stderr}")
