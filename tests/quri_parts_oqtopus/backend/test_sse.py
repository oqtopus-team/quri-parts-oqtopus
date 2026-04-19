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
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from oqtopus_client import OqtopusClient
from oqtopus_client import OqtopusConfig as ClientConfig
from oqtopus_client.services.job_results import (
    OqtopusEstimationJobResult,
    OqtopusMultiManualJobResult,
    OqtopusSamplingJobResult,
    OqtopusSseJobResult,
)
from pytest_mock import MockerFixture
from quri_parts.backend import BackendError

from quri_parts_oqtopus.backend import (
    OqtopusSamplingJob,
    OqtopusSseBackend,
    OqtopusSseJob,
)
from quri_parts_oqtopus.backend.config import OqtopusConfig

if TYPE_CHECKING:
    from quri_parts_oqtopus.models.jobs.results.estimation import (
        OqtopusEstimationResult,
    )
    from quri_parts_oqtopus.models.jobs.results.sampling import OqtopusSamplingResult


def get_dummy_job_result(job_id: str = "dummy_id") -> OqtopusSseJobResult:
    return OqtopusSseJobResult(
        job_id=job_id,
        shots=1,
        name="test",
        device_id="test_device",
        job_type="sse",
        status="submitted",
        job_info={"program": ["dummy"], "result": {"sampling": {"counts": {"0": 1}}}},
        client=get_dummy_client(),
    )


def get_dummy_job(job_id: str = "dummy_id") -> OqtopusSseJob:
    job = get_dummy_job_result(job_id)
    return OqtopusSseJob(job=job, client=get_dummy_client())


def _job_info_with_result(result: dict) -> dict:
    return {
        "input": {
            "program": ["dummy"],
            "operator": [],
            "sse_program": None,
        },
        "result": result,
        "message": None,
    }


def get_sampling_job_result(job_id: str = "dummy_sampling") -> OqtopusSamplingJobResult:
    return OqtopusSamplingJobResult(
        job_id=job_id,
        shots=1,
        name="test",
        device_id="test_device",
        job_type="sampling",
        status="succeeded",
        job_info=_job_info_with_result({"sampling": {"counts": {"0": 1}}}),
        client=get_dummy_client(),
    )


def get_estimation_job_result(
    job_id: str = "dummy_estimation",
) -> OqtopusEstimationJobResult:
    return OqtopusEstimationJobResult(
        job_id=job_id,
        shots=1,
        name="test",
        device_id="test_device",
        job_type="estimation",
        status="succeeded",
        job_info=_job_info_with_result({"estimation": {"exp_value": 0.5, "stds": 0.1}}),
        client=get_dummy_client(),
    )


def get_multi_manual_job_result(
    job_id: str = "dummy_multi_manual",
) -> OqtopusMultiManualJobResult:
    return OqtopusMultiManualJobResult(
        job_id=job_id,
        shots=1,
        name="test",
        device_id="test_device",
        job_type="multi_manual",
        status="succeeded",
        job_info=_job_info_with_result({"sampling": {"counts": {"0": 1}}}),
        client=get_dummy_client(),
    )


class _WaitedJobStub:
    def __init__(self, job_id: str, status: str, job_result: object) -> None:
        self.job_id = job_id
        self.status = status
        self._job_result = job_result

    def get_job_result(self) -> object:
        return self._job_result


class _WaitClientStub:
    def __init__(self, waited_job: _WaitedJobStub) -> None:
        self._waited_job = waited_job
        self.calls: list[tuple[str, float, float | None]] = []

    def wait(
        self, job_id: str, interval: float, timeout: float | None
    ) -> _WaitedJobStub:
        self.calls.append((job_id, interval, timeout))
        return self._waited_job


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


def get_dummy_client() -> OqtopusClient:
    return OqtopusClient(ClientConfig(base_url="dummy_url", api_token="dummy_token"))  # noqa: S106


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory and yield the path to it.

    Yields:
        Path: Path to the temporary directory.
    """
    temp_dir = tempfile.TemporaryDirectory()
    yield Path(temp_dir.name)
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
        assert sse_job._client.base_url == config.url  # noqa: SLF001

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
        assert sse_job._client.base_url == config.url  # noqa: SLF001
        mock_obj.assert_called_once()

    def test_run_sse(self, mocker: MockerFixture, temp_python: Path) -> None:
        # Arrange
        mock_submit_job = mocker.patch(
            "oqtopus_client.OqtopusClient.submit_job",
            return_value=SimpleNamespace(job_id="dummy_id"),
        )
        job = get_dummy_job_result()
        mocker.patch(
            "oqtopus_client.OqtopusClient.get_job",
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
        spec = mock_submit_job.call_args.args[0]
        assert spec.program == read_data.decode("utf-8")
        assert spec.job_type.value == "sse"

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
            "quri_parts_oqtopus.backend.jobs.sse.Path.open",
            new_callable=mocker.mock_open,
            read_data=read_data,
        )
        mocker.patch(
            "quri_parts_oqtopus.backend.jobs.sse.len", return_value=10 * 1024 * 1024 + 1
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
            "oqtopus_client.OqtopusClient.submit_job",
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
        spec = mock_submit_job.call_args.args[0]
        assert spec.program == read_data.decode("utf-8")
        assert spec.job_type.value == "sse"

    def test_result_sampling(self) -> None:
        # Arrange
        job_id = "dummy_sampling_sse"
        waited_result = get_sampling_job_result(job_id="dummy_sampling")
        wait_client = _WaitClientStub(
            _WaitedJobStub(job_id=job_id, status="succeeded", job_result=waited_result)
        )
        sse_job = OqtopusSseJob(
            job=get_dummy_job_result(job_id=job_id),
            client=wait_client,  # type: ignore[arg-type]
        )

        # Act
        result = cast("OqtopusSamplingResult", sse_job.result(timeout=12.0, wait=3.0))

        # Assert
        assert result.counts == {0: 1}
        assert wait_client.calls == [(job_id, 3.0, 12.0)]

    def test_result_multi_manual(self) -> None:
        # Arrange
        job_id = "dummy_multi_manual_sse"
        result_job = get_multi_manual_job_result(job_id="dummy_multi_manual")
        wait_client = _WaitClientStub(
            _WaitedJobStub(job_id=job_id, status="succeeded", job_result=result_job)
        )
        # already-final status should skip wait()
        sse_job = OqtopusSseJob(
            job=get_dummy_job_result(job_id=job_id),
            client=wait_client,  # type: ignore[arg-type]
        )
        sse_job._job = _WaitedJobStub(  # type: ignore[assignment] # noqa: SLF001
            job_id=job_id,
            status="succeeded",
            job_result=result_job,
        )

        # Act
        result = cast("OqtopusSamplingResult", sse_job.result(timeout=7.0, wait=0.5))

        # Assert
        assert result.counts == {0: 1}
        assert wait_client.calls == []

    def test_result_estimation(self) -> None:
        # Arrange
        job_id = "dummy_estimation_sse"
        waited_result = get_estimation_job_result(job_id="dummy_estimation")
        wait_client = _WaitClientStub(
            _WaitedJobStub(job_id=job_id, status="succeeded", job_result=waited_result)
        )
        sse_job = OqtopusSseJob(
            job=get_dummy_job_result(job_id=job_id),
            client=wait_client,  # type: ignore[arg-type]
        )

        # Act
        result = cast("OqtopusEstimationResult", sse_job.result(timeout=15.0, wait=5.0))

        # Assert
        assert result.exp_value == pytest.approx(0.5)
        assert result.stds == pytest.approx(0.1)
        assert wait_client.calls == [(job_id, 5.0, 15.0)]

    def test_result_invalid_result_type(self) -> None:
        # Arrange
        job_id = "dummy_invalid_result_sse"
        wait_client = _WaitClientStub(
            _WaitedJobStub(job_id=job_id, status="succeeded", job_result=object())
        )
        sse_job = OqtopusSseJob(
            job=get_dummy_job_result(job_id=job_id),
            client=wait_client,  # type: ignore[arg-type]
        )

        # Act and Assert
        with pytest.raises(BackendError, match=r"The job result is not a valid type."):
            sse_job.result(timeout=1.0, wait=0.1)

    def test_download_log(self, mocker: MockerFixture) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        job = get_dummy_job()
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded, file_name="dummy.zip"),
        )

        # Act
        path = job.download_log()

        # Assert
        assert path == str(PurePath(Path.cwd()).joinpath("dummy.zip"))
        mock_obj.assert_called_once_with(job.job_id)
        assert Path("dummy.zip").exists()
        assert Path("dummy.zip").read_bytes() == zip_bytes

        # cleanup
        Path("dummy.zip").unlink()

    def test_download_log_with_jobid(self, mocker: MockerFixture) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        job = get_dummy_job(job_id="dummy_id2")
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded, file_name="dummy.zip"),
        )

        # Act
        path = job.download_log()

        # Assert
        assert path == str(PurePath(Path.cwd()).joinpath("dummy.zip"))
        mock_obj.assert_called_once_with("dummy_id2")
        assert Path("dummy.zip").exists()
        assert Path("dummy.zip").read_bytes() == zip_bytes

        # cleanup
        Path("dummy.zip").unlink()

    def test_download_log_with_path(
        self, mocker: MockerFixture, temp_dir: Path
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        job = get_dummy_job()
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded, file_name="dummy.zip"),
        )

        # Act
        path = job.download_log(save_dir=str(temp_dir.absolute()))

        # Assert
        assert path == str(temp_dir.joinpath("dummy.zip"))
        mock_obj.assert_called_once_with(job.job_id)
        assert temp_dir.joinpath("dummy.zip").exists()
        assert temp_dir.joinpath("dummy.zip").read_bytes() == zip_bytes

    def test_download_log_invalid_path(self, mocker: MockerFixture) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        job = get_dummy_job()
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded, file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(
            ValueError, match=r"The destination path does not exist: destination/path"
        ):
            # path does not exist
            job.download_log(save_dir="destination/path")

        # Assert
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_not_directory(
        self, mocker: MockerFixture, temp_zip: Path
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        job = get_dummy_job()
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded, file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(
            ValueError,
            match=rf"The destination path is not a directory: {temp_zip.absolute()}",
        ):
            # not a directory, but a file
            job.download_log(save_dir=str(temp_zip.absolute()))

        # Assert
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_conflict_path(
        self, mocker: MockerFixture, temp_zip: Path
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        job = get_dummy_job()
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            # the file name is the same as the existing file
            return_value=SimpleNamespace(file=encoded, file_name=temp_zip.name),
        )

        # Act
        with pytest.raises(
            ValueError, match=rf"The file already exists: {temp_zip.absolute()}"
        ):
            # the file already exists in the directory
            job.download_log(save_dir=str(temp_zip.parent))

        # Assert
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_request_failure(self, mocker: MockerFixture) -> None:
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.jobs.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        job = get_dummy_job()
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            side_effect=Exception("test exception"),
        )

        # Act
        with pytest.raises(
            BackendError, match=r"To perform sse on OQTOPUS Cloud is failed."
        ):
            job.download_log(save_dir="destination/path")

        # Assert
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_invalid_response_none(self, mocker: MockerFixture) -> None:
        # Arrange
        job = get_dummy_job()
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=None,
        )

        # Act
        with pytest.raises(
            BackendError,
            match=r"To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data.",  # noqa: E501
        ):
            job.download_log(save_dir="destination/path")

        # Assert
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_invalid_response_none_file(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        job = get_dummy_job()
        # file is None
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=None, file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(BackendError) as e:
            job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_invalid_response_none_filename(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        job = get_dummy_job()
        # filename is None
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded, file_name=None),
        )

        # Act
        with pytest.raises(BackendError) as e:
            job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_invalid_response_empty_file(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        job = get_dummy_job()
        # file is emtpy
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file="", file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(BackendError) as e:
            job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_invalid_response_empty_filename(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded = get_dummy_base64zip()

        job = get_dummy_job()
        # filename is emtpy
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded, file_name=""),
        )

        # Act
        with pytest.raises(BackendError) as e:
            job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_invalid_response_no_file(self, mocker: MockerFixture) -> None:
        # Arrange
        job = get_dummy_job()
        # contains no file
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(BackendError) as e:
            job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_invalid_response_no_filename(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        job = get_dummy_job()
        # contains no filename
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded),
        )

        # Act
        with pytest.raises(BackendError) as e:
            job.download_log(save_dir="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job.job_id)

    def test_download_log_with_backend_class(self, mocker: MockerFixture) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        backend = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded, file_name="dummy.zip"),
        )
        backend._job = job  # noqa: SLF001

        # Act
        path = backend.download_log()

        # Assert
        assert path == str(PurePath(Path.cwd()).joinpath("dummy.zip"))
        mock_obj.assert_called_once_with(job.job_id)
        assert Path("dummy.zip").exists()
        assert Path("dummy.zip").read_bytes() == zip_bytes

        # cleanup
        Path("dummy.zip").unlink()

    def test_download_log_with_backend_class_with_jobid(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        backend = OqtopusSseBackend(get_dummy_config())
        job = get_dummy_job()
        mock_obj = mocker.patch(
            "oqtopus_client.OqtopusClient.get_sselog",
            return_value=SimpleNamespace(file=encoded, file_name="dummy.zip"),
        )
        mocker.patch(
            "quri_parts_oqtopus.backend.jobs.base.OqtopusJobBackendBase.retrieve_job",
            return_value=job,
        )

        # Act
        path = backend.download_log(job_id="dummy_id")

        # Assert
        assert path == str(PurePath(Path.cwd()).joinpath("dummy.zip"))
        mock_obj.assert_called_once_with("dummy_id")
        assert Path("dummy.zip").exists()
        assert Path("dummy.zip").read_bytes() == zip_bytes

        # cleanup
        Path("dummy.zip").unlink()

    def test_download_log_with_backend_class_with_no_jobid(self) -> None:
        # Arrange
        backend = OqtopusSseBackend(get_dummy_config())

        # Act and Assert
        with pytest.raises(
            ValueError, match=r"job_id is not set and no job has been executed."
        ):
            backend.download_log()

    def test_download_log_with_backend_class_with_invalid_jobid(
        self, mocker: MockerFixture
    ) -> None:
        # Arrange
        backend = OqtopusSseBackend(get_dummy_config())
        job = OqtopusSamplingJob
        mocker.patch(
            "quri_parts_oqtopus.backend.jobs.base.OqtopusJobBackendBase.retrieve_job",
            return_value=job,
        )

        # Act and Assert
        with pytest.raises(
            TypeError, match=r"The job with id dummy_id is not an SSE job."
        ):
            backend.download_log(job_id="dummy_id")
