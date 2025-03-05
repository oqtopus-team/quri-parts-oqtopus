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
import zipfile
from pathlib import Path, PurePath

import pytest
from pytest_mock import MockerFixture
from quri_parts.backend import BackendError

from quri_parts_oqtopus.backend import (
    OqtopusConfig,
    OqtopusSseJob,
)
from quri_parts_oqtopus.rest import (
    JobsJobDef,
    JobsSubmitJobResponse,
)
from quri_parts_oqtopus.rest.models.jobs_get_sselog_response import (
    JobsGetSselogResponse,
)


def get_dummy_job(job_id: str = "dummy_id") -> JobsJobDef:
    return JobsJobDef(
        job_id=job_id,
        shots=1,
        name="test",
        device_id="test_device",
        job_type="sse",
        status="submitted",
        job_info="dummy_info",
    )


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


def get_dummy_base64zip() -> str:
    zip_stream = io.BytesIO()
    dummy_zip = zipfile.ZipFile(zip_stream, "w", compression=zipfile.ZIP_DEFLATED)
    dummy_zip.writestr("dummy.log", "dumm_text")
    dummy_zip.close()
    encoded = base64.b64encode(zip_stream.getvalue()).decode()
    return encoded, zip_stream.getvalue()


def get_dummy_config() -> OqtopusConfig:
    return OqtopusConfig("dummpy_url", "dummy_api_token")


class TestOqtopusSseJob:  # noqa: PLR0904
    def test_init(self):
        # Arrange
        config = get_dummy_config()

        # Act
        sse_job = OqtopusSseJob(config)

        # Assert
        assert sse_job.config == config
        assert sse_job.job is None
        assert sse_job._job_api.api_client.configuration.host == config.url  # noqa: SLF001

    def test_init_default(self, mocker: MockerFixture):
        # Arrange
        config = OqtopusConfig("dummpy_url_def", "dummy_api_token_def")
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.backend.OqtopusConfig.from_file",
            return_value=config,
        )

        # Act
        sse_job = OqtopusSseJob()

        # Assert
        assert sse_job.config == config
        assert sse_job.job is None
        assert sse_job._job_api.api_client.configuration.host == config.url  # noqa: SLF001
        mock_obj.assert_called_once()

    def test_run_sse(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("quri_parts_oqtopus.backend.sse.Path.exists", return_value=True)
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
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.open",
            new_callable=mocker.mock_open,
            read_data=read_data,
        )

        sse_job = OqtopusSseJob(get_dummy_config())

        # Act
        ret_job = sse_job.run_sse(
            "dummy/dummy.py", device_id="test_device", name="test"
        )

        # Assert
        assert ret_job.job_id == job.job_id
        sj_call = mock_submit_job.call_args
        assert sj_call.kwargs["body"].job_info.program[0] == base64.b64encode(
            read_data
        ).decode("utf-8")
        assert sj_call.kwargs["body"].job_type == "sse"

    def test_run_sse_invalid_arg(self):
        # Act
        sse_job = OqtopusSseJob(get_dummy_config())
        with pytest.raises(ValueError, match=r"file_path is not set.") as e:
            sse_job.run_sse(None, device_id="test_device", name="test")

        # Assert
        assert str(e.value) == "file_path is not set."

    def test_run_sse_nofile(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("quri_parts_oqtopus.backend.sse.Path.exists", return_value=False)
        sse_job = OqtopusSseJob(get_dummy_config())

        # Act
        with pytest.raises(
            ValueError, match=r"The file does not exist: dummy/dummy.py"
        ) as e:
            sse_job.run_sse("dummy/dummy.py", device_id="test_device", name="test")

        # Assert
        assert str(e.value) == "The file does not exist: dummy/dummy.py"

    def test_run_invalid_extention(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("quri_parts_oqtopus.backend.sse.Path.exists", return_value=True)
        sse_job = OqtopusSseJob(get_dummy_config())

        # Act
        with pytest.raises(
            ValueError, match=r"The file is not python file: dummy/dummy.y"
        ) as e:
            sse_job.run_sse("dummy/dummy.y", device_id="test_device", name="test")

        # Assert
        assert str(e.value) == "The file is not python file: dummy/dummy.y"

    def test_run_largefile(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("quri_parts_oqtopus.backend.sse.Path.exists", return_value=True)
        read_data = b'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\n\nh q[0];\ncx q[0], q[1];'  # noqa: E501
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.open",
            new_callable=mocker.mock_open,
            read_data=read_data,
        )
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.len", return_value=10 * 1024 * 1024 + 1
        )
        sse_job = OqtopusSseJob(get_dummy_config())

        # Act
        with pytest.raises(
            ValueError, match=r"size of the base64 encoded file is larger than"
        ) as e:
            sse_job.run_sse("dummy/dummy.py", device_id="test_device", name="test")

        # Assert
        assert (
            str(e.value)
            == f"size of the base64 encoded file is larger than {10 * 1024 * 1024}"
        )

    def test_run_request_failure(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("quri_parts_oqtopus.backend.sse.Path.exists", return_value=True)
        read_data = b'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\n\nh q[0];\ncx q[0], q[1];'  # noqa: E501
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.open",
            new_callable=mocker.mock_open,
            read_data=read_data,
        )
        mock_submit_job = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.submit_job",
            side_effect=Exception("test exception"),
        )

        sse_job = OqtopusSseJob(get_dummy_config())
        with pytest.raises(BackendError) as e:
            # Act
            sse_job.run_sse("dummy/dummy.py", device_id="test_device", name="test")

        # Assert
        assert str(e.value) == "To perform sse on OQTOPUS Cloud is failed."
        sj_call = mock_submit_job.call_args
        assert sj_call.kwargs["body"].job_info.program[0] == base64.b64encode(
            read_data
        ).decode("utf-8")
        assert sj_call.kwargs["body"].job_type == "sse"

    def test_download_log(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("quri_parts_oqtopus.backend.sse.Path.exists", return_value=False)
        open_mock = mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.open", new_callable=mocker.mock_open
        )

        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        path = sse_job.download_log()

        # Assert
        handle = open_mock()
        handle.write.assert_called_once_with(zip_bytes)
        assert path == str(PurePath(Path.cwd()).joinpath("dummy.zip"))
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_with_jobid(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("quri_parts_oqtopus.backend.sse.Path.exists", return_value=False)
        open_mock = mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.open", new_callable=mocker.mock_open
        )

        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        sse_job = OqtopusSseJob(get_dummy_config())
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        path = sse_job.download_log(job_id="dummy_id2")

        # Assert
        handle = open_mock()
        handle.write.assert_called_once_with(zip_bytes)
        assert path == str(PurePath(Path.cwd()).joinpath("dummy.zip"))
        mock_obj.assert_called_once_with(job_id="dummy_id2")

    def test_download_log_invalid_jobid(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("quri_parts_oqtopus.backend.sse.Path.exists", return_value=False)

        sse_job = OqtopusSseJob(get_dummy_config())
        sse_job.job = None
        # Act
        with pytest.raises(ValueError, match=r"job_id is not set.") as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert str(e.value) == "job_id is not set."

    def test_download_log_with_path(self, mocker: MockerFixture):
        # Arrange
        mocked_path = mocker.MagicMock()
        mocker.patch.object(mocked_path, "exists", side_effect=[True, False])
        open_mock = mocker.patch.object(
            mocked_path, "open", new_callable=mocker.mock_open
        )
        mocker.patch("quri_parts_oqtopus.backend.sse.Path", return_value=mocked_path)

        # make zip stream to be downloaded
        encoded, zip_bytes = get_dummy_base64zip()

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        path = sse_job.download_log(save_path="destination/path")

        # Assert
        handle = open_mock()
        handle.write.assert_called_once_with(zip_bytes)
        assert path == str(PurePath("destination/path").joinpath("dummy.zip"))
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_path(self, mocker: MockerFixture):
        # Arrange
        mocked_path = mocker.MagicMock()
        mocker.patch.object(mocked_path, "exists", side_effect=[False, False])
        open_mock = mocker.patch.object(
            mocked_path, "open", new_callable=mocker.mock_open
        )
        mocker.patch("quri_parts_oqtopus.backend.sse.Path", return_value=mocked_path)

        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(
            ValueError, match=r"The destination path does not exist: destination/path"
        ) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert str(e.value) == "The destination path does not exist: destination/path"
        mock_obj.assert_called_once_with(job_id=job.job_id)
        open_mock.assert_not_called()

    def test_download_log_conflict_path(self, mocker: MockerFixture):
        # Arrange
        mocked_path = mocker.MagicMock()
        mocker.patch.object(mocked_path, "exists", side_effect=[True, True])
        open_mock = mocker.patch.object(
            mocked_path, "open", new_callable=mocker.mock_open
        )
        mocker.patch("quri_parts_oqtopus.backend.sse.Path", return_value=mocked_path)

        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(
            ValueError, match=r"The file already exists: destination/path/dummy.zip"
        ) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert str(e.value) == "The file already exists: destination/path/dummy.zip"
        mock_obj.assert_called_once_with(job_id=job.job_id)
        open_mock.assert_not_called()

    def test_download_log_request_failure(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            side_effect=Exception("test exception"),
        )

        # Act
        with pytest.raises(
            BackendError, match=r"To perform sse on OQTOPUS Cloud is failed."
        ) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert str(e.value) == "To perform sse on OQTOPUS Cloud is failed."
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_none(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=None,
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_1(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # file is None
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=None, file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_2(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # filename is None
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name=None),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_3(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # file is emtpy
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file="", file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_4(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        # make zip stream to be downloaded
        encoded = get_dummy_base64zip()

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # filename is emtpy
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded, file_name=""),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_5(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # contains no file
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file_name="dummy.zip"),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)

    def test_download_log_invalid_response_6(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.backend.sse.Path.exists",
            side_effect=lambda path: path == "destination/path",
        )

        # make zip stream to be downloaded
        encoded, _ = get_dummy_base64zip()

        sse_job = OqtopusSseJob(get_dummy_config())
        job = get_dummy_job()
        sse_job.job = job
        # contains no filename
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_sselog",
            return_value=JobsGetSselogResponse(file=encoded),
        )

        # Act
        with pytest.raises(BackendError) as e:
            sse_job.download_log(save_path="destination/path")

        # Assert
        assert (
            str(e.value)
            == "To perform sse on OQTOPUS Cloud is failed. The response does not contain valid file data."  # noqa: E501
        )
        mock_obj.assert_called_once_with(job_id=job.job_id)
