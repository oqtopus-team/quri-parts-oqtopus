# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# from __future__ import annotations

# from typing import TYPE_CHECKING

# if TYPE_CHECKING:
#     from pytest_mock import MockerFixture

import base64
import io
import tempfile
import zipfile
from collections.abc import Generator
from pathlib import Path, PurePath
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from quri_parts.backend import BackendError

from quri_parts_oqtopus.backend import (
    OqtopusSamplingJob,
    OqtopusSseBackend,
)
from quri_parts_oqtopus.backend.config import OqtopusConfig

config_file_data = """[default]
url=default_url
api_token=default_api_token

[test]
url=test_url
api_token=test_api_token

[wrong]
url=test_url
"""

qasm_data = """OPENQASM 3;
include "stdgates.inc";
qubit[2] q;

h q[0];
cx q[0], q[1];"""


def get_dummy_base64zip() -> tuple[str, bytes]:
    zip_stream = io.BytesIO()
    dummy_zip = zipfile.ZipFile(zip_stream, "w", compression=zipfile.ZIP_DEFLATED)
    dummy_zip.writestr("dummy.log", "dumm_text")
    dummy_zip.close()
    encoded = base64.b64encode(zip_stream.getvalue()).decode()
    return encoded, zip_stream.getvalue()


def get_dummy_config() -> OqtopusConfig:
    return OqtopusConfig("dummpy_url", "dummy_api_token")


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory and yield the path to it.

    Yields:
        Path: Path to the temporary directory.
    """
    temp_dir = tempfile.TemporaryDirectory()
    path = Path(temp_dir.name)
    yield path
    temp_dir.cleanup()


@pytest.fixture
def temp_zip() -> Generator[Path, None, None]:
    """
    Create a temporary zip file in a temporary directory and yield the path to it.

    Yields:
        Path: Path to the temporary zip file.
    """
    temp_dir = tempfile.TemporaryDirectory()
    dir_path = Path(temp_dir.name).absolute()
    with tempfile.NamedTemporaryFile(
        suffix=".zip", dir=dir_path, delete=False
    ) as temp_file:
        path = Path(temp_file.name)
        yield path
        path.unlink()
        temp_dir.cleanup()


@pytest.fixture
def temp_python() -> Generator[Path, None, None]:
    """
    Create a temporary python file in a temporary directory and yield the path to it.

    Yields:
        Path: Path to the temporary python file.
    """
    temp_dir = tempfile.TemporaryDirectory()
    dir_path = Path(temp_dir.name).absolute()
    with tempfile.NamedTemporaryFile(
        suffix=".py", dir=dir_path, delete=False
    ) as temp_file:
        path = Path(temp_file.name)
        yield path
        path.unlink()
        temp_dir.cleanup()


class TestOqtopusSseBackend:
    DEFAULT_JOB_ID: str = "dummy_job_id"
    DEFAULT_FILENAME: str = f"sse_log_{DEFAULT_JOB_ID}.zip"

    @pytest.fixture
    def setup_mock_retrieve_job(
        self, mocker: MockerFixture
    ) -> tuple[MagicMock, MagicMock, bytes]:
        """
        Pytest fixture to set up common mock job and retrieve_job patch.

        Returns:
            tuple[MagicMock, MagicMock, bytes]: A tuple containing:
                - mock_retrieved_job (MagicMock): The mocked job
                - mock_retrieve_job (MagicMock): The mocked retrieve_job method.
                - zip_bytes (bytes): The raw dummy zip file content.
        """
        encoded_data, zip_bytes = get_dummy_base64zip()
        mock_retrieved_job = MagicMock(spec=OqtopusSamplingJob)
        mock_retrieved_job.job_id = self.DEFAULT_JOB_ID
        mock_retrieved_job.job_info = {
            "result": {
                "sampling": {
                    "counts": {"0000": 490, "0001": 10, "0110": 20, "1111": 480}
                }
            },
            "sse_log": encoded_data,
        }
        mock_retrieve_job = mocker.patch(
            "quri_parts_oqtopus.backend.sse.OqtopusSamplingBackend.retrieve_job",
            return_value=mock_retrieved_job,
        )

        return mock_retrieved_job, mock_retrieve_job, zip_bytes

    def test_init(self, mocker: MockerFixture) -> None:
        # Arrange
        config = get_dummy_config()

        mock_sampling_backend_class = mocker.patch(
            "quri_parts_oqtopus.backend.sse.OqtopusSamplingBackend"
        )

        # Act
        sse_backend = OqtopusSseBackend(config)

        # Assert
        assert sse_backend.config == config
        mock_sampling_backend_class.assert_called_once_with(config)
        assert sse_backend.job is None

    def test_init_default(self, mocker: MockerFixture) -> None:
        # Arrange
        config = get_dummy_config()

        mock_config = mocker.patch(
            "quri_parts_oqtopus.backend.OqtopusConfig.from_file",
            return_value=config,
        )
        mock_sampling_backend_class = mocker.patch(
            "quri_parts_oqtopus.backend.sse.OqtopusSamplingBackend"
        )

        # Act
        sse_backend = OqtopusSseBackend()

        # Assert
        assert sse_backend.config == config
        mock_config.assert_called_once()
        mock_sampling_backend_class.assert_called_once_with(config)
        assert sse_backend.job is None

    def test_run_sse(self, mocker: MockerFixture, temp_python: Path) -> None:
        # Arrange
        sse_backend = OqtopusSseBackend(get_dummy_config())

        mock_job = MagicMock(spec=OqtopusSamplingJob)
        mock_sample_qasm = mocker.patch(
            "quri_parts_oqtopus.backend.sse.OqtopusSamplingBackend.sample_qasm",
            return_value=mock_job,
        )

        read_data = b'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\n\nh q[0];\ncx q[0], q[1];'  # noqa: E501
        temp_python.write_bytes(read_data)

        # Act
        ret_job = sse_backend.run_sse(
            str(temp_python.absolute()), device_id="test_device", name="test"
        )

        # Assert
        # Check that the backend method was called with the correct parameters
        mock_sample_qasm.assert_called_once_with(
            program=[base64.b64encode(read_data).decode("utf-8")],
            shots=1,
            name="test",
            device_id="test_device",
            description=None,
            job_type="sse",
        )
        # Check result
        assert ret_job == mock_job

    def test_run_sse_invalid_arg(self) -> None:
        # Arrange
        sse_job = OqtopusSseBackend(get_dummy_config())

        # Act
        with pytest.raises(ValueError, match=r"file_path is not set.") as e:
            sse_job.run_sse(None, device_id="test_device", name="test")  # type: ignore[arg-type]

        # Assert
        assert str(e.value) == "file_path is not set."

    def test_run_sse_nofile(self) -> None:
        # Arrange
        sse_job = OqtopusSseBackend(get_dummy_config())

        # Act
        with pytest.raises(
            ValueError, match=r"The file does not exist: dummy/dummy.py"
        ) as e:
            sse_job.run_sse("dummy/dummy.py", device_id="test_device", name="test")

        # Assert
        assert str(e.value) == "The file does not exist: dummy/dummy.py"

    def test_run_invalid_extention(self, temp_zip: Path) -> None:
        # Arrange
        sse_job = OqtopusSseBackend(get_dummy_config())

        # Act
        with pytest.raises(
            ValueError, match=rf"The file is not python file: {temp_zip.absolute()}"
        ):
            sse_job.run_sse(
                str(temp_zip.absolute()), device_id="test_device", name="test"
            )

    def test_run_largefile(self, mocker: MockerFixture, temp_python: Path) -> None:
        # Arrange
        sse_job = OqtopusSseBackend(get_dummy_config())

        read_data = b'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\n\nh q[0];\ncx q[0], q[1];'  # noqa: E501
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.open",
            new_callable=mocker.mock_open,
            read_data=read_data,
        )
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.len", return_value=10 * 1024 * 1024 + 1
        )

        # Act and Assert
        with pytest.raises(
            ValueError,
            match=rf"size of the base64 encoded file is larger than {10 * 1024 * 1024}",
        ):
            sse_job.run_sse(
                str(temp_python.absolute()), device_id="test_device", name="test"
            )

    def test_run_request_failure(
        self, mocker: MockerFixture, temp_python: Path
    ) -> None:
        # Arrange
        sse_backend = OqtopusSseBackend(get_dummy_config())

        mock_sample_qasm = mocker.patch(
            "quri_parts_oqtopus.backend.sse.OqtopusSamplingBackend.sample_qasm",
            side_effect=Exception("test exception"),
        )

        read_data = b'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\n\nh q[0];\ncx q[0], q[1];'  # noqa: E501
        temp_python.write_bytes(read_data)

        with pytest.raises(
            BackendError, match=r"To perform sse on OQTOPUS Cloud is failed."
        ):
            # Act
            sse_backend.run_sse(
                str(temp_python.absolute()), device_id="test_device", name="test"
            )

        # Assert
        # Check that the backend method was called with the correct parameters
        mock_sample_qasm.assert_called_once_with(
            program=[base64.b64encode(read_data).decode("utf-8")],
            shots=1,
            name="test",
            device_id="test_device",
            description=None,
            job_type="sse",
        )

    def test_download_log(
        self, setup_mock_retrieve_job: tuple[MagicMock, MagicMock, bytes]
    ) -> None:
        # Arrange
        sse_backend = OqtopusSseBackend(get_dummy_config())
        mock_job = MagicMock(spec=OqtopusSamplingJob)
        mock_job.job_id = self.DEFAULT_JOB_ID
        sse_backend.job = mock_job

        _, mock_retrieve_job, zip_bytes = setup_mock_retrieve_job

        # Act
        path = sse_backend.download_log()

        # Assert
        mock_retrieve_job.assert_called_once_with(job_id=self.DEFAULT_JOB_ID)
        assert path == str(PurePath(Path.cwd()).joinpath(self.DEFAULT_FILENAME))
        assert Path(self.DEFAULT_FILENAME).exists()
        assert Path(self.DEFAULT_FILENAME).read_bytes() == zip_bytes

        # cleanup
        Path(self.DEFAULT_FILENAME).unlink()

    def test_download_log_with_jobid(
        self, setup_mock_retrieve_job: tuple[MagicMock, MagicMock, bytes]
    ) -> None:
        # Arrange
        another_job_id = "dummy_job_id_2"
        another_filename = f"sse_log_{another_job_id}.zip"

        sse_backend = OqtopusSseBackend(get_dummy_config())

        mock_job = MagicMock(spec=OqtopusSamplingJob)
        mock_job.job_id = self.DEFAULT_JOB_ID
        sse_backend.job = mock_job

        mock_retrieved_job, mock_retrieve_job, zip_bytes = setup_mock_retrieve_job
        mock_retrieved_job.job_id = another_job_id

        # Act
        path = sse_backend.download_log(job_id=another_job_id)

        # Assert
        mock_retrieve_job.assert_called_once_with(job_id=another_job_id)
        assert path == str(PurePath(Path.cwd()).joinpath(another_filename))
        assert Path(another_filename).exists()
        assert Path(another_filename).read_bytes() == zip_bytes

        # cleanup
        Path(another_filename).unlink()

    def test_download_log_invalid_jobid(self, temp_dir: Path) -> None:
        # Arrange
        sse_backend = OqtopusSseBackend(get_dummy_config())

        # Act
        with pytest.raises(ValueError, match=r"job_id is not set.") as e:
            sse_backend.download_log(save_dir=str(temp_dir.absolute()))

        # Assert
        assert str(e.value) == "job_id is not set."

    def test_download_log_with_path(
        self,
        temp_dir: Path,
        setup_mock_retrieve_job: tuple[MagicMock, MagicMock, bytes],
    ) -> None:
        # Arrange
        sse_backend = OqtopusSseBackend(get_dummy_config())

        mock_job = MagicMock(spec=OqtopusSamplingJob)
        mock_job.job_id = self.DEFAULT_JOB_ID
        sse_backend.job = mock_job

        _, mock_retrieve_job, zip_bytes = setup_mock_retrieve_job

        # Act
        path = sse_backend.download_log(save_dir=str(temp_dir.absolute()))

        # Assert
        mock_retrieve_job.assert_called_once_with(job_id=self.DEFAULT_JOB_ID)
        assert path == str(temp_dir.joinpath(self.DEFAULT_FILENAME))
        assert Path(temp_dir.joinpath(self.DEFAULT_FILENAME)).exists()
        assert Path(temp_dir.joinpath(self.DEFAULT_FILENAME)).read_bytes() == zip_bytes

        # cleanup
        Path(temp_dir.joinpath(self.DEFAULT_FILENAME)).unlink()

    def test_download_log_invalid_path(
        self, setup_mock_retrieve_job: tuple[MagicMock, MagicMock, bytes]
    ) -> None:
        sse_backend = OqtopusSseBackend(get_dummy_config())

        mock_job = MagicMock(spec=OqtopusSamplingJob)
        mock_job.job_id = self.DEFAULT_JOB_ID
        sse_backend.job = mock_job

        _, mock_retrieve_job, _ = setup_mock_retrieve_job

        # Act
        with pytest.raises(
            ValueError, match=r"The destination path does not exist: destination/path"
        ):
            # path does not exist
            sse_backend.download_log(save_dir="destination/path")

        # Assert
        mock_retrieve_job.assert_called_once_with(job_id=self.DEFAULT_JOB_ID)

    def test_download_log_not_directory(
        self,
        setup_mock_retrieve_job: tuple[MagicMock, MagicMock, bytes],
        temp_zip: Path,
    ) -> None:
        sse_backend = OqtopusSseBackend(get_dummy_config())

        mock_job = MagicMock(spec=OqtopusSamplingJob)
        mock_job.job_id = self.DEFAULT_JOB_ID
        sse_backend.job = mock_job

        _, mock_retrieve_job, _ = setup_mock_retrieve_job

        # Act
        with pytest.raises(
            ValueError,
            match=rf"The destination path is not a directory: {temp_zip.absolute()}",
        ):
            # not a directory, but a file
            sse_backend.download_log(save_dir=str(temp_zip.absolute()))

        # Assert
        mock_retrieve_job.assert_called_once_with(job_id=self.DEFAULT_JOB_ID)

    def test_download_log_conflict_path(
        self, setup_mock_retrieve_job: tuple[MagicMock, MagicMock, bytes]
    ) -> None:
        # Arrange
        sse_backend = OqtopusSseBackend(get_dummy_config())
        mock_job = MagicMock(spec=OqtopusSamplingJob)
        mock_job.job_id = self.DEFAULT_JOB_ID
        sse_backend.job = mock_job

        _, mock_retrieve_job, _ = setup_mock_retrieve_job

        # create sse_log file
        Path(self.DEFAULT_FILENAME).touch()

        # Act
        with pytest.raises(
            ValueError,
            match=(
                r"The file already exists: "
                + str(PurePath(Path.cwd()).joinpath(self.DEFAULT_FILENAME))
            ),
        ):
            # the file already exists in the directory
            sse_backend.download_log()

        # Assert
        mock_retrieve_job.assert_called_once_with(job_id=self.DEFAULT_JOB_ID)

        # cleanup
        Path(self.DEFAULT_FILENAME).unlink()

    def test_download_log_request_failure(self, mocker: MockerFixture) -> None:
        # Arrange
        sse_backend = OqtopusSseBackend(get_dummy_config())
        mock_job = MagicMock(spec=OqtopusSamplingJob)
        mock_job.job_id = self.DEFAULT_JOB_ID
        sse_backend.job = mock_job

        mock_retrieve_job = mocker.patch(
            "quri_parts_oqtopus.backend.sse.OqtopusSamplingBackend.retrieve_job",
            side_effect=Exception("test exception"),
        )

        # Act
        with pytest.raises(
            BackendError, match=r"To perform sse on OQTOPUS Cloud is failed."
        ):
            sse_backend.download_log(save_dir="destination/path")

        # Assert
        mock_retrieve_job.assert_called_once_with(job_id=self.DEFAULT_JOB_ID)

    def test_download_log_no_sse_log_data(self, mocker: MockerFixture) -> None:
        # Arrange
        sse_backend = OqtopusSseBackend(get_dummy_config())
        mock_job = MagicMock(spec=OqtopusSamplingJob)
        mock_job.job_id = self.DEFAULT_JOB_ID
        sse_backend.job = mock_job

        mock_retrieved_job = MagicMock(spec=OqtopusSamplingJob)
        mock_retrieved_job.job_id = self.DEFAULT_JOB_ID
        mock_retrieved_job.job_info = {
            "result": {
                "sampling": {
                    "counts": {"0000": 490, "0001": 10, "0110": 20, "1111": 480}
                }
            }
        }
        mock_retrieve_job = mocker.patch(
            "quri_parts_oqtopus.backend.sse.OqtopusSamplingBackend.retrieve_job",
            return_value=mock_retrieved_job,
        )

        # Act
        with pytest.raises(
            BackendError,
            match=r"To perform sse on OQTOPUS Cloud is failed. The response does not contain sse_log data.",  # noqa: E501
        ):
            sse_backend.download_log(save_dir="destination/path")

        # Assert
        mock_retrieve_job.assert_called_once_with(job_id=self.DEFAULT_JOB_ID)
