import io
import json
import os
import requests
from io import BytesIO
from zipfile import ZipFile

from quri_parts_oqtopus.rest import (
    JobsJobInfoDownloadPresignedURL,
    JobsJobInfoUploadPresignedURL,
)


class OqtopusStorage:
    """
    Provides methods for accessing oqtopus cloud storage via presign URLs
    """

    @staticmethod
    def _extract_zip_object(zip_buffer: BytesIO) -> dict:
        with ZipFile(zip_buffer, "r") as zip_arch:
            json_file_path_list = zip_arch.namelist()

            if len(json_file_path_list) == 1:
                # one .zip = one json file
                with zip_arch.open(json_file_path_list[0]) as json_file:
                    value = json.loads(json_file.read())
                    return value
            else:
                # TODO: raise exception
                return {}

    @staticmethod
    def download(presigned_url: JobsJobInfoDownloadPresignedURL) -> dict:
        """
        Downloads and extracts json data from an oqtopus cloud storage .zip file

        Args:
            presigned_url (JobsJobInfoDownloadPresignedURL): presigned URL of target .zip file to download

        Raises:
            e: _description_

        Returns:
            dict: loaded json data extracted from the .zip
        """
        with io.BytesIO() as zip_buffer:
            resp = requests.get(url=str(presigned_url))
            zip_buffer.write(resp.content)
            zip_buffer.flush()
            zip_buffer.seek(0)
            try:
                return OqtopusStorage._extract_zip_object(zip_buffer)
            except Exception as e:
                # TODO: improve error handling
                raise e

    @staticmethod
    def upload(presigned_url: JobsJobInfoUploadPresignedURL, data: dict) -> None:
        """Uploads data to oqtopus cloud storage as .zip file

        Args:
            presigned_url (JobsJobInfoUploadPresignedURL): presigned URL for upload
            data (dict): data to upload
        """
        with io.BytesIO() as zip_buffer:
            zip_buffer.name = os.path.basename(presigned_url.fields.key)
            with ZipFile(file=zip_buffer, mode="w") as zip_arch:
                zip_arch.writestr(
                    zinfo_or_arcname=f"{os.path.splitext(zip_buffer.name)[0]}.json",
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
                        os.path.basename(zip_buffer.name),
                        zip_buffer,
                        "application/zip",
                    )
                },
            )

            # TODO handle upload failure
