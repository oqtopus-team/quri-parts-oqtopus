import json
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import requests
from requests.exceptions import RequestException

from quri_parts_oqtopus.rest import (
    JobsJobInfoDownloadPresignedURL,
    JobsJobInfoUploadPresignedURL,
)


class OqtopusStorageError(Exception):
    """Custom exception for OqtopusStorage operations."""


class OqtopusStorage:
    """Provides methods for accessing oqtopus cloud storage via presign URLs."""

    DEFAULT_TIMEOUT_S = 60

    @staticmethod
    def _extract_zip_object(zip_bytes: bytes) -> dict[str, Any]:
        try:
            with ZipFile(BytesIO(zip_bytes), "r") as zip_arch:
                json_file_path_list = zip_arch.namelist()

                if len(json_file_path_list) != 1:
                    msg = (
                        "Expected one file in single ZIP archive, "
                        f"but found {len(json_file_path_list)}."
                    )
                    raise OqtopusStorageError(msg)

                with zip_arch.open(json_file_path_list[0]) as json_file:
                    data = json.loads(json_file.read())
                    if not isinstance(data, dict):
                        msg = (
                            "Expected JSON root to be an object (dict)"
                            f" but got {type(data).__name__}."
                        )
                        raise OqtopusStorageError(msg)
                    return data

        except BadZipFile as e:
            msg = "Invalid ZIP file"
            raise OqtopusStorageError(msg) from e
        except json.JSONDecodeError as e:
            msg = "Invalid JSON in ZIP file"
            raise OqtopusStorageError(msg) from e

    @staticmethod
    def download(
        presigned_url: JobsJobInfoDownloadPresignedURL,
        timeout_s: int = DEFAULT_TIMEOUT_S,
    ) -> dict[str, Any]:
        """Download and extract JSON data from an oqtopus cloud storage .zip file.

        Args:
            presigned_url (JobsJobInfoDownloadPresignedURL):
                presigned URL of target .zip file to download
            timeout_s: operation timeout in seconds

        Returns:
            dict[str, Any]: loaded json data extracted from the .zip

        Raises:
            OqtopusStorageError: If the download, extraction, or JSON parsing fails.

        """
        try:
            resp = requests.get(url=str(presigned_url), timeout=timeout_s)
            resp.raise_for_status()
            return OqtopusStorage._extract_zip_object(resp.content)
        except RequestException as e:
            msg = f"Network error during download: {e}"
            raise OqtopusStorageError(msg) from e

    @staticmethod
    def upload(
        presigned_url: JobsJobInfoUploadPresignedURL,
        data: dict[str, Any],
        timeout_s: int = DEFAULT_TIMEOUT_S,
    ) -> None:
        """Upload data to oqtopus cloud storage as .zip file.

        Args:
            presigned_url (JobsJobInfoUploadPresignedURL): presigned URL for upload
            data (dict[str, Any]): data to upload
            timeout_s: operation timeout in seconds

        Raises:
            OqtopusStorageError: If the upload fails.

        """
        try:
            with BytesIO() as zip_buffer:
                zip_buffer.name = Path(presigned_url.fields.key).name
                with ZipFile(
                    file=zip_buffer, mode="w", compression=ZIP_DEFLATED
                ) as zip_arch:
                    zip_arch.writestr(
                        zinfo_or_arcname=f"{Path(zip_buffer.name).stem}.json",
                        data=json.dumps(data),
                    )
                zip_buffer.seek(0)

                # swagger-codegen generates JobsJobInfoUploadPresignedURLFields class
                # and changes fields names e.g. AWSAccessKeyId -> aws_access_key_id
                # we get the true field names
                original_fields = {
                    presigned_url.fields.attribute_map[k]: v
                    for (k, v) in presigned_url.fields.to_dict().items()
                }

                resp = requests.post(
                    url=presigned_url.url,
                    data=original_fields,
                    files={
                        "file": (
                            Path(zip_buffer.name).name,
                            zip_buffer,
                            "application/zip",
                        )
                    },
                    timeout=timeout_s,
                )
                resp.raise_for_status()

        except RequestException as e:
            msg = f"Network error during upload: {e}"
            raise OqtopusStorageError(msg) from e
