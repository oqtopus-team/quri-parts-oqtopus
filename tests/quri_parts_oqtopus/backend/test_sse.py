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

import pytest
from pytest_mock import MockerFixture
from quri_parts.backend import BackendError

from quri_parts_oqtopus.backend import (
    OqtopusSamplingJob,
    OqtopusSseBackend,
)
from quri_parts_oqtopus.backend.config import OqtopusConfig
from quri_parts_oqtopus.rest import (
    JobApi,
    JobsJobDef,
    JobsSubmitJobResponse,
)
from quri_parts_oqtopus.rest.models.jobs_get_sselog_response import (
    JobsGetSselogResponse,
)


def get_dummy_job(job_id: str = "dummy_id") -> OqtopusSamplingJob:
    job = JobsJobDef(
        job_id=job_id,
        shots=1,
        name="test",
        device_id="test_device",
        job_type="sse",
        status="submitted",
        job_info="dummy_info",
    )
    return OqtopusSamplingJob(job=job, job_api=JobApi())


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


class TestOqtopusSseBackend:  # noqa: PLR0904
    def test_init(self) -> None:
        # Arrange
        config = get_dummy_config()

        # Act
        sse_job = OqtopusSseBackend(config)

        # Assert
        assert sse_job.config == config
        assert sse_job.job is None
        assert sse_job._job_api.api_client.configuration.host == config.url  # noqa: SLF001

    def test_init_default(self, mocker: MockerFixture) -> None:
        # Arrange
        config = OqtopusConfig("dummpy_url_def", "dummy_api_token_def")
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.backend.OqtopusConfig.from_file",
            return_value=config,
        )

        # Act
        sse_job = OqtopusSseBackend()

        # Assert
        assert sse_job.config == config
        assert sse_job.job is None
        assert sse_job._job_api.api_client.configuration.host == config.url  # noqa: SLF001
        mock_obj.assert_called_once()

    def test_run_sse(self, mocker: MockerFixture, temp_python: Path) -> None:
        # Arrange
        mock_submit_job = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.submit_job",
            return_value=JobsSubmitJobResponse(job_id="dummy_id"),
        )
        job = get_dummy_job()
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            return_value=job,
        )
        read_data = b'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\n\nh q[0];\ncx q[0], q[1];'  # noqa: E501
        temp_python.write_bytes(read_data)

        sse_job = OqtopusSseBackend(get_dummy_config())

        # Act
        ret_job = sse_job.run_sse(
            str(temp_python.absolute()), device_id="test_device", name="test"
        )

        # Assert
        assert ret_job.job_id == job.job_id
        sj_call = mock_submit_job.call_args
        assert sj_call.kwargs["body"].job_info.program[0] == base64.b64encode(
            read_data
        ).decode("utf-8")
        assert sj_call.kwargs["body"].job_type == "sse"

    def test_run_sse_invalid_arg(self) -> None:
        # Act
        sse_job = OqtopusSseBackend(get_dummy_config())
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
        read_data = b'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\n\nh q[0];\ncx q[0], q[1];'  # noqa: E501
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.open",
            new_callable=mocker.mock_open,
            read_data=read_data,
        )
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.len", return_value=10 * 1024 * 1024 + 1
        )
        sse_job = OqtopusSseBackend(get_dummy_config())

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
        read_data = b'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\n\nh q[0];\ncx q[0], q[1];'  # noqa: E501
        temp_python.write_bytes(read_data)
        mock_submit_job = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.submit_job",
            side_effect=Exception("test exception"),
        )

        sse_job = OqtopusSseBackend(get_dummy_config())
        with pytest.raises(
            BackendError, match=r"To perform sse on OQTOPUS Cloud is failed."
        ):
            # Act
            sse_job.run_sse(
                str(temp_python.absolute()), device_id="test_device", name="test"
            )

        # Assert
        sj_call = mock_submit_job.call_args
        assert sj_call.kwargs["body"].job_info.program[0] == base64.b64encode(
            read_data
        ).decode("utf-8")
        assert sj_call.kwargs["body"].job_type == "sse"

    def test_download_log(self, mocker: MockerFixture) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        path = sse_job.download_log()

        # Assert
        assert path == str(PurePath(Path.cwd()).joinpath("dummy.zip"))
        mock_obj.assert_called_once_with(job_id=job.job_id)
        assert Path("dummy.zip").exists()
        assert Path("dummy.zip").read_bytes() == zip_bytes

        # cleanup
        Path("dummy.zip").unlink()

    def test_download_log_with_jobid(self, mocker: MockerFixture) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        sse_job = OqtopusSseBackend(get_dummy_config())
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        path = sse_job.download_log(job_id="dummy_id2")

        # Assert
        assert path == str(PurePath(Path.cwd()).joinpath("dummy.zip"))
        mock_obj.assert_called_once_with(job_id="dummy_id2")
        assert Path("dummy.zip").exists()
        assert Path("dummy.zip").read_bytes() == zip_bytes

        # cleanup
        Path("dummy.zip").unlink()

    def test_download_log_invalid_jobid(self, temp_dir: Path) -> None:
        # Arrange
        sse_job = OqtopusSseBackend(get_dummy_config())
        sse_job.job = None
        # Act
        with pytest.raises(ValueError, match=r"job_id is not set.") as e:
            sse_job.download_log(save_dir=str(temp_dir.absolute()))

        # Assert
        assert str(e.value) == "job_id is not set."

    def test_download_log_with_path(
        self, mocker: MockerFixture, temp_dir: Path
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        path = sse_job.download_log(save_dir=str(temp_dir.absolute()))

        # Assert
        assert path == str(temp_dir.joinpath("dummy.zip"))
        mock_obj.assert_called_once_with(job_id=job.job_id)
        assert temp_dir.joinpath("dummy.zip").exists()
        assert temp_dir.joinpath("dummy.zip").read_bytes() == zip_bytes

    def test_download_log_invalid_path(self, mocker: MockerFixture) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(
            ValueError, match=r"The destination path does not exist: destination/path"
        ):
            # path does not exist
            sse_job.download_log(save_dir="destination/path")

        # Assert
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_not_directory(
        self, mocker: MockerFixture, temp_zip: Path
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(
            ValueError,
            match=rf"The destination path is not a directory: {temp_zip.absolute()}",
        ):
            # not a directory, but a file
            sse_job.download_log(save_dir=str(temp_zip.absolute()))

        # Assert
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_conflict_path(
        self, mocker: MockerFixture, temp_zip: Path
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            # the file name is the same as the existing file
            return_value=JobsGetSselogResponse(file=encoded, file_name=temp_zip.name),
        )

        # Act
        with pytest.raises(
            ValueError, match=rf"The file already exists: {temp_zip.absolute()}"
        ):
            # the file already exists in the directory
            sse_job.download_log(save_dir=str(temp_zip.parent))

        # Assert
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_request_failure(self, mocker: MockerFixture) -> None:
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            side_effect=Exception("test exception"),
        )

        # Act
        with pytest.raises(
            BackendError, match=r"To perform sse on OQTOPUS Cloud is failed."
        ):
            sse_job.download_log(save_dir="destination/path")

        # Assert
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_none(self, mocker: MockerFixture) -> None:
        # Arrange
        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=None,
        )

        # Act
        with pytest.raises(
            BackendError,
            match=r"To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data.",  # noqa: E501
        ):
            sse_job.download_log(save_dir="destination/path")

        # Assert
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_none_file(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # file is None
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=None, file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_none_filename(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # filename is None
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name=None),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_empty_file(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # file is emtpy
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file="", file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_empty_filename(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded = get_dummy_base64zip()

        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # filename is emtpy
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name=""),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_no_file(self, mocker: MockerFixture) -> None:
        # Arrange
        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # contains no file
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_no_filename(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        sse_job = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # contains no filename
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)
