import logging
import os
from pathlib import Path

import requests
from humanfriendly import format_size

# Logger
logging.basicConfig()
logger = logging.getLogger(__name__)


def create_job_input_redis_key(namespace: str, job_name: str):
    return f"{namespace}-{job_name}"


def download_file(
    url: str,
    headers: dict[str, str] | None,
    local_file: Path,
    chunk_size: int = 1024 * 1024,
) -> None:
    """
    Downloads a remote URL to a local file.

    :param url: The remote URL.
    :param headers: Dictionary of HTTP Headers
    :param local_filename: The name of the local file to save the downloaded content.
    :param chunk_size: The size in bytes of each chunk. Defaults to 1024.
    """
    # Check if the local file already exists
    if os.path.exists(local_file):
        file_size = format_size(os.path.getsize(local_file))
        logger.info(
            f"Local file '{local_file}' ({file_size}) already exists. Skipping download."
        )
        return

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(local_file), exist_ok=True)

    # Stream the file download
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(local_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

        file_size = format_size(os.path.getsize(local_file))
        logger.info(f"{local_file} ({file_size}) downloaded successfully.")
