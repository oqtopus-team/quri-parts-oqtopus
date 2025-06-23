import io
import json
import requests
from io import BytesIO
from zipfile import ZipFile


class OqtopusStorage:
    """
    Provides methods for accessing oqtopus cloud storage via presign URLs
    """

    @staticmethod
    def _extract_zip_object(zip_buffer: BytesIO) -> dict:
        with ZipFile(zip_buffer, 'r') as zip_arch:
            json_file_path_list = zip_arch.namelist()

            if (len(json_file_path_list) == 1):
                # one .zip = one json file
                with zip_arch.open(json_file_path_list[0]) as json_file:
                    value = json.loads(json_file.read())
                    return value
            else:
                # TODO: raise exception
                return {}

    @staticmethod
    def download(presign_url: str) -> dict:
        """
        Downloads and extracts json data from an oqtopus cloud storage .zip file

        Args:
            presign_url (str): presign URL of target .zip file to download

        Raises:
            e: _description_

        Returns:
            dict: loaded json data extracted from the .zip
        """
        with io.BytesIO() as zip_buffer:
            resp = requests.get(url=presign_url)
            zip_buffer.write(resp.content)
            zip_buffer.flush()
            zip_buffer.seek(0)
            try:
                return OqtopusStorage._extract_zip_object(zip_buffer)
            except Exception as e:
                # TODO: improve error handling
                raise e
