import json
from collections.abc import Callable
from io import BytesIO
from typing import Any, cast
from unittest.mock import Mock
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from pytest_mock import MockerFixture
from requests.exceptions import HTTPError

from quri_parts_oqtopus.backend.storage import OqtopusStorage, OqtopusStorageError
from quri_parts_oqtopus.rest.models import (
    JobsJobInfoDownloadPresignedURL,
    JobsJobInfoUploadPresignedURL,
    JobsJobInfoUploadPresignedURLFields,
)

MOCK_DOWNLOAD_URL = "http://host:port/storage_base/input.zip"
MOCK_UPLOAD_URL = "https://mock.storage/upload/"
MOCK_FILE_KEY = "dummy_job_id/input.zip"


@pytest.fixture
def file_content() -> dict[str, Any]:
    return {
        "program": 'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;',  # noqa: E501
        "operator": [
            {"pauli": "X0 X1", "coeff": 1.0},
            {"pauli": "Z0 Z1", "coeff": 1.0},
        ],
    }


@pytest.fixture
def create_zip_bytes():
    def _create(data: str) -> bytes:
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zip_arch:
            zip_arch.writestr("input.json", data)
        return zip_buffer.getvalue()

    return _create


@pytest.fixture
def mock_download_url() -> JobsJobInfoDownloadPresignedURL:
    return cast("JobsJobInfoDownloadPresignedURL", MOCK_DOWNLOAD_URL)


@pytest.fixture
def mock_upload_url():
    return JobsJobInfoUploadPresignedURL(
        url=MOCK_UPLOAD_URL,
        fields=JobsJobInfoUploadPresignedURLFields(
            key=MOCK_FILE_KEY,
            x_amz_security_token="TEST_TOKEN",  # noqa: S106
            aws_access_key_id="TEST_KEY",
            policy="TEST_POLICY",
            signature="TEST_SIG",
        ),
    )


class TestStorage:
    def test_download_success(
        self,
        mocker: MockerFixture,
        create_zip_bytes: Callable[[str], bytes],
        file_content: dict[str, Any],
        mock_download_url: JobsJobInfoDownloadPresignedURL,
    ):
        """Tests successful download and data extraction"""

        # Arrange
        mock_get = mocker.patch("quri_parts_oqtopus.backend.storage.requests.get")
        mock_get.return_value.content = create_zip_bytes(json.dumps(file_content))
        mock_get.return_value.raise_for_status.return_value = None

        # Act
        result = OqtopusStorage.download(mock_download_url, timeout_s=30)

        # Assert result
        assert result == file_content

        mock_get.assert_called_once_with(url=MOCK_DOWNLOAD_URL, timeout=30)
        mock_get.return_value.raise_for_status.assert_called_once()

    def test_download_malformed_json(
        self,
        mocker: MockerFixture,
        create_zip_bytes: Callable[[str], bytes],
        mock_download_url: JobsJobInfoDownloadPresignedURL,
    ):
        """Tests handling of json errors"""

        # Arrange
        mock_get = mocker.patch("quri_parts_oqtopus.backend.storage.requests.get")
        mock_get.return_value.content = create_zip_bytes('{"key": "value",}')
        mock_get.return_value.raise_for_status.return_value = None

        with pytest.raises(
            OqtopusStorageError,
            match="Invalid JSON in ZIP file",
        ):
            OqtopusStorage.download(mock_download_url)

        mock_get.assert_called_once()
        mock_get.return_value.raise_for_status.assert_called_once()

    def test_download_invalid_json(
        self,
        mocker: MockerFixture,
        create_zip_bytes: Callable[[str], bytes],
        mock_download_url: JobsJobInfoDownloadPresignedURL,
    ):
        """Tests handling of json errors"""

        # Arrange
        mock_get = mocker.patch("quri_parts_oqtopus.backend.storage.requests.get")
        mock_get.return_value.content = create_zip_bytes(json.dumps(["1", "2"]))
        mock_get.return_value.raise_for_status.return_value = None

        # Act & Assert
        with pytest.raises(
            OqtopusStorageError,
            match=r"Expected JSON root to be an object \(dict\) but got list.",
        ):
            OqtopusStorage.download(mock_download_url)

        mock_get.assert_called_once()
        mock_get.return_value.raise_for_status.assert_called_once()

    def test_download_malformed_zip(
        self,
        mocker: MockerFixture,
        mock_download_url: JobsJobInfoDownloadPresignedURL,
    ):
        """Tests handling of zip file errors"""

        # Arrange
        mock_get = mocker.patch("quri_parts_oqtopus.backend.storage.requests.get")
        mock_get.return_value.content = b""
        mock_get.return_value.raise_for_status.return_value = None

        # Act & Assert
        with pytest.raises(OqtopusStorageError, match="Invalid ZIP file"):
            OqtopusStorage.download(mock_download_url)

        mock_get.assert_called_once()
        mock_get.return_value.raise_for_status.assert_called_once()

    def test_download_http_error(
        self,
        mocker: MockerFixture,
        mock_download_url: JobsJobInfoDownloadPresignedURL,
    ):
        """Tests that a bad HTTP status from requests.get is handled."""

        # Arrange
        mock_get = mocker.patch("quri_parts_oqtopus.backend.storage.requests.get")
        mock_get.return_value.content = b""
        mock_get.return_value.raise_for_status.side_effect = HTTPError(
            "404 Client Error"
        )

        # Act & Assert
        with pytest.raises(OqtopusStorageError, match="Network error during download"):
            OqtopusStorage.download(mock_download_url)

        mock_get.assert_called_once()
        mock_get.return_value.raise_for_status.assert_called_once()

    def test_upload_success(
        self,
        mocker: MockerFixture,
        mock_upload_url: JobsJobInfoUploadPresignedURL,
        file_content: dict[str, Any],
    ):
        """
        Tests a successful upload by mocking requests.post
        and inspecting its call.
        """

        # Arrange
        captured_zip_content = []

        def capture_and_mock_post(**kwargs: Any) -> Mock:
            """
            Side effect to capture the file content before the buffer is closed.
            Returns:
                Mock: mocked response
            """
            file_tuple = kwargs.get("files", {}).get("file")
            if file_tuple:
                file_object = file_tuple[1]
                captured_zip_content.append(file_object.read())

            mock_response = mocker.Mock()
            mock_response.raise_for_status.return_value = None
            return mock_response

        mock_post = mocker.patch(
            "quri_parts_oqtopus.backend.storage.requests.post",
            side_effect=capture_and_mock_post,
        )

        # Act
        OqtopusStorage.upload(mock_upload_url, file_content)

        # Assert
        # 1. Check that our mock was called exactly once
        mock_post.assert_called_once()

        # 2. Check URL
        call_args = mock_post.call_args
        assert call_args.kwargs["url"] == MOCK_UPLOAD_URL

        # 3. Check the remapped form fields
        expected_form_fields = {
            "key": MOCK_FILE_KEY,
            "x-amz-security-token": "TEST_TOKEN",
            "AWSAccessKeyId": "TEST_KEY",
            "policy": "TEST_POLICY",
            "signature": "TEST_SIG",
        }
        assert call_args.kwargs["data"] == expected_form_fields

        # 4. Check the file upload details and content
        uploaded_files = call_args.kwargs["files"]
        assert "file" in uploaded_files

        filename, _, content_type = uploaded_files["file"]
        assert filename == "input.zip"
        assert content_type == "application/zip"

        # Unzip the in-memory file object to verify its contents
        assert len(captured_zip_content) == 1
        zip_content = captured_zip_content[0]

        with ZipFile(BytesIO(zip_content), "r") as zip_arch:
            assert zip_arch.namelist() == ["input.json"]
            unzipped_data = json.loads(zip_arch.read("input.json"))
            assert unzipped_data == file_content

    def test_upload_http_error(
        self,
        mocker: MockerFixture,
        mock_upload_url: JobsJobInfoUploadPresignedURL,
        file_content: dict[str, Any],
    ):
        """Tests that a bad HTTP status from requests.get is handled."""

        # Arrange
        mock_post = mocker.patch("quri_parts_oqtopus.backend.storage.requests.post")
        mock_post.return_value.raise_for_status.side_effect = HTTPError("404 Not Found")

        # Act & Assert
        with pytest.raises(OqtopusStorageError, match="Network error during upload"):
            OqtopusStorage.upload(mock_upload_url, file_content)

        mock_post.assert_called_once()
        mock_post.return_value.raise_for_status.assert_called_once()
