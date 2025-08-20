import io
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import requests

from quri_parts_oqtopus.rest import (
    JobsJobInfoDownloadPresignedURL,
    JobsJobInfoUploadPresignedURL,
)


class OqtopusStorage:
    """Provides methods for accessing oqtopus cloud storage via presign URLs."""

    @staticmethod
    def _extract_zip_object(zip_buffer: BytesIO) -> dict:
        with ZipFile(zip_buffer, "r") as zip_arch:
            json_file_path_list = zip_arch.namelist()

            if len(json_file_path_list) == 1:
                # one .zip = one json file
                with zip_arch.open(json_file_path_list[0]) as json_file:
                    return json.loads(json_file.read())
            else:
                return {}

    @staticmethod
    def download(
        presigned_url: JobsJobInfoDownloadPresignedURL, timeout_s: int = 60
    ) -> dict:
        """Download and extract JSON data from an oqtopus cloud storage .zip file.

        Args:
            presigned_url (JobsJobInfoDownloadPresignedURL):
                presigned URL of target .zip file to download
            timeout_s: operation timeout in seconds

        Returns:
            dict: loaded json data extracted from the .zip

        """
        with io.BytesIO() as zip_buffer:
            resp = requests.get(url=str(presigned_url), timeout=timeout_s)
            zip_buffer.write(resp.content)
            zip_buffer.flush()
            zip_buffer.seek(0)

            return OqtopusStorage._extract_zip_object(zip_buffer)

    @staticmethod
    def upload(
        presigned_url: JobsJobInfoUploadPresignedURL, data: dict, timeout_s: int = 60
    ) -> None:
        """Upload data to oqtopus cloud storage as .zip file.

        Args:
            presigned_url (JobsJobInfoUploadPresignedURL): presigned URL for upload
            data (dict): data to upload
            timeout_s: operation timeout in seconds

        """
        with io.BytesIO() as zip_buffer:
            zip_buffer.name = Path(presigned_url.fields.key).name
            with ZipFile(file=zip_buffer, mode="w") as zip_arch:
                zip_arch.writestr(
                    zinfo_or_arcname=f"{Path(zip_buffer.name).stem}.json",
                    data=json.dumps(data),
                )
            zip_buffer.seek(0)

            # swagger-codegen generates JobsJobInfoUploadPresignedURLFields class and
            # changes fields names e.g. AWSAccessKeyId -> aws_access_key_id
            # we get the true field names
            original_fields = {
                presigned_url.fields.attribute_map[k]: v
                for (k, v) in presigned_url.fields.to_dict().items()
            }

            requests.post(
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
