# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import sys
import time
from unittest.mock import mock_open, patch

import pytest
from pytest_mock.plugin import MockerFixture
from quri_parts.backend import BackendError
from quri_parts.circuit import QuantumCircuit

from quri_parts_oqtopus.backend.config import OqtopusConfig
from quri_parts_oqtopus.backend.sampling import (
    OqtopusSamplingBackend,
    OqtopusSamplingJob,
    OqtopusSamplingResult,
)
from quri_parts_oqtopus.rest import (
    JobApi,
    JobsJobDef,
    JobsJobInfo,
    JobsJobResult,
    JobsSubmitJobInfo,
    JobsSubmitJobRequest,
    JobsSubmitJobResponse,
    JobsTranspileResult,
)

config_file_data = """[default]
url=default_url
api_token=default_api_token

[test]
url=test_url
api_token=test_api_token

[option]
url=test_url
api_token=test_api_token
proxy=https://testproxy:port

[wrong]
url=test_url
"""

qasm_data = """OPENQASM 3;
include "stdgates.inc";
qubit[2] q;

h q[0];
cx q[0], q[1];"""

qasm_data_with_measure = """OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];
c = measure q;"""

qasm_data2 = """OPENQASM 3;
include "stdgates.inc";
qubit[3] q;

h q[0];
cx q[0], q[1];
ry(0.1) q[2];"""

qasm_array_json = json.dumps({"qasm": [qasm_data, qasm_data2, qasm_data]})


def get_dummy_job(status: str = "succeeded") -> JobsJobDef:
    return JobsJobDef(
        job_id="dummy_job_id",
        name="dummy_name",
        description="dummy_description",
        job_type="sampling",
        status=status,
        device_id="demmy_device_id",
        shots=1000,
        job_info=JobsJobInfo(
            program=[
                'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;'  # noqa: E501
            ],
            transpile_result=JobsTranspileResult(
                stats='{"before": {"n_qubits": 2, "n_gates": 4, "n_gates_1q": 3, "n_gates_2q": 1, "depth": 4}, "after": {"n_qubits": 6, "n_gates": 4, "n_gates_1q": 3, "n_gates_2q": 1, "depth": 4}}',  # noqa: E501
                transpiled_program='OPENQASM 3; include "stdgates.inc"; qubit[2] q; bit[2] c; rz(1.5707963267948932) q[0]; sx q[0]; rz(1.5707963267948966) q[0]; cx q[0], q[1]; c = measure q;',  # noqa: E501
                virtual_physical_mapping='{"0": 0, "1": 1}',
            ),
            result={
                "sampling": JobsJobResult(
                    counts={"00": 490, "01": 10, "10": 20, "11": 480},
                )
            },
        ),
        transpiler_info={
            "transpiler_lib": "qiskit",
            "transpiler_options": {"optimization_level": 2},
        },
        simulator_info={},
        mitigation_info={},
        execution_time=5.123,
        submitted_at=datetime.datetime(2000, 1, 2, 3, 4, 1),  # noqa: DTZ001
        ready_at=datetime.datetime(2000, 1, 2, 3, 4, 2),  # noqa: DTZ001
        running_at=datetime.datetime(2000, 1, 2, 3, 4, 3),  # noqa: DTZ001
        ended_at=datetime.datetime(2000, 1, 2, 3, 4, 4),  # noqa: DTZ001
    )


def get_dummy_multimanual_job(status: str = "succeeded") -> JobsJobDef:
    job = get_dummy_job(status)
    job.job_type = "multi_manual"
    job.job_info.program = [
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;',  # noqa: E501
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[3] q;\nbit[3] c;\n\nh q[0];\ncx q[0], q[1];\nry(0.1) q[2];\nc = measure q;',  # noqa: E501
        'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;',  # noqa: E501
    ]
    job.job_info.result["sampling"] = JobsJobResult(
        counts={"0000": 490, "0001": 10, "0110": 20, "1111": 480},
        divided_counts={
            "0": {"00": 490, "01": 10, "10": 20, "11": 480},
            "1": {"00": 500, "01": 20, "11": 480},
        },
    )
    return job


def get_dummy_JobsSubmitJobRequest(  # noqa: N802
    job_type: str | None = "sampling",
    program: list[str] | None = None,
) -> JobsSubmitJobRequest:
    if program is None:
        program = [
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;'  # noqa: E501
        ]

    return JobsSubmitJobRequest(
        name="dummy_name",
        description="dummy_description",
        device_id="dummy_device_id",
        job_type=job_type,
        job_info=JobsSubmitJobInfo(program=program),
        transpiler_info={
            "transpiler_lib": "qiskit",
            "transpiler_options": {"optimization_level": 2},
        },
        simulator_info={},
        mitigation_info={},
        shots=1000,
    )


def get_dummy_JobsSubmitJobResponse(  # noqa: N802
    job_id: str | None = "dummy_job_id",
) -> JobsSubmitJobResponse:
    return JobsSubmitJobResponse(job_id=job_id)


def get_dummy_config() -> OqtopusConfig:
    return OqtopusConfig("dummpy_url", "dummy_api_token")


class TestOqtopusSamplingResult:
    def test_init_error(self):
        # case: counts does not exist in result
        result_without_count = {
            "transpile_result": {
                "virtual_physical_mapping": {
                    "0": 0,
                    "1": 1,
                },
            },
        }
        with pytest.raises(ValueError, match="'counts' does not exist in result"):
            OqtopusSamplingResult(result_without_count)

    def test_counts(self):
        # Arrange
        result_dict = {
            "counts": {
                0: 6000,
                2: 4000,
            },
            "transpile_result": {
                "virtual_physical_mapping": {
                    "0": 0,
                    "1": 1,
                },
            },
        }
        result = OqtopusSamplingResult(result_dict)

        # Act
        actual = result.counts

        # Assert
        expected = {
            0: 6000,
            2: 4000,
        }
        assert actual == expected

    def test_repr(self):
        # Arrage
        result_dict = {
            "counts": {
                0: 6000,
                2: 4000,
            },
            "divided_counts": {
                "0": {
                    "0": 10000,
                },
                "1": {
                    "0": 6000,
                    "1": 4000,
                },
            },
        }
        result = OqtopusSamplingResult(result_dict)

        # Act
        actual = repr(result)

        # Assert
        expected = str(result_dict)
        assert actual == expected


class TestOqtopusSamplingJob:
    def test_init_error(self):
        # case: job is None
        with pytest.raises(ValueError, match="'job' should not be None"):
            OqtopusSamplingJob(job=None, job_api="dummy")

        # case: job_api is None
        job_raw = get_dummy_job()
        with pytest.raises(ValueError, match="'job_api' should not be None"):
            OqtopusSamplingJob(job=job_raw, job_api=None)

    def test_properties(self):
        # Arrange
        job_raw = get_dummy_job()
        job = OqtopusSamplingJob(job=job_raw, job_api="dummy")

        # Act & Assert
        assert job.job_id == "dummy_job_id"
        assert job.name == "dummy_name"
        assert job.description == "dummy_description"
        assert job.job_type == "sampling"
        assert job.status == "succeeded"
        assert job.device_id == "demmy_device_id"
        assert job.shots == 1000
        assert job.job_info["program"] == [
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;'  # noqa: E501
        ]
        assert (
            job.job_info["transpile_result"]["stats"]
            == '{"before": {"n_qubits": 2, "n_gates": 4, "n_gates_1q": 3, "n_gates_2q": 1, "depth": 4}, "after": {"n_qubits": 6, "n_gates": 4, "n_gates_1q": 3, "n_gates_2q": 1, "depth": 4}}'  # noqa: E501
        )
        assert (
            job.job_info["transpile_result"]["transpiled_program"]
            == 'OPENQASM 3; include "stdgates.inc"; qubit[2] q; bit[2] c; rz(1.5707963267948932) q[0]; sx q[0]; rz(1.5707963267948966) q[0]; cx q[0], q[1]; c = measure q;'  # noqa: E501
        )
        assert (
            job.job_info["transpile_result"]["virtual_physical_mapping"]
            == '{"0": 0, "1": 1}'
        )
        assert job.result().counts == {0: 490, 1: 10, 2: 20, 3: 480}
        assert job.transpiler_info == {
            "transpiler_lib": "qiskit",
            "transpiler_options": {"optimization_level": 2},
        }
        assert job.simulator_info == {}
        assert job.mitigation_info == {}
        assert job.execution_time == 5.123
        assert job.submitted_at == datetime.datetime(2000, 1, 2, 3, 4, 1)  # noqa: DTZ001
        assert job.ready_at == datetime.datetime(2000, 1, 2, 3, 4, 2)  # noqa: DTZ001
        assert job.running_at == datetime.datetime(2000, 1, 2, 3, 4, 3)  # noqa: DTZ001
        assert job.ended_at == datetime.datetime(2000, 1, 2, 3, 4, 4)  # noqa: DTZ001

    def test_refresh(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            return_value=get_dummy_job(),
        )
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        job.refresh()

        # Assert
        assert job.status == "succeeded"

    def test_wait_for_completion(self, mocker: MockerFixture):
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            side_effect=[
                get_dummy_job("succeeded"),
                get_dummy_job("failed"),
                get_dummy_job("cancelled"),
            ],
        )

        # case1: status is "success"
        # Arrange
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        actual = job.wait_for_completion()

        # Assert
        assert actual is not None
        assert actual.status == "succeeded"

        # case2: status is "failure"
        # Arrange
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        actual = job.wait_for_completion()

        # Assert
        assert actual is not None
        assert actual.status == "failed"

        # case3: status is "cancelled"
        # Arrange
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        actual = job.wait_for_completion()

        # Assert
        assert actual is not None
        assert actual.status == "cancelled"

    def test_wait_for_completion__wait(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            side_effect=[
                get_dummy_job("running"),
                get_dummy_job("succeeded"),
            ],
        )

        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        start_time = time.time()
        actual = job.wait_for_completion(wait=3.0)
        elapsed_time = time.time() - start_time

        # Assert
        assert actual is not None
        assert actual.status == "succeeded"
        assert elapsed_time >= 3.0

    def test_wait_for_completion__timeout(self, mocker: MockerFixture):
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            side_effect=[
                get_dummy_job("running"),
                get_dummy_job("running"),
                get_dummy_job("running"),
                get_dummy_job("running"),
                get_dummy_job("running"),
            ],
        )

        # Arrange
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        start_time = time.time()
        actual = job.wait_for_completion(timeout=10.0, wait=3.0)
        elapsed_time = time.time() - start_time

        # Assert
        assert actual is None
        assert elapsed_time >= 10.0

    def test_result(self, mocker: MockerFixture):
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            side_effect=[
                get_dummy_job("succeeded"),
                get_dummy_job("failed"),
                get_dummy_job("cancelled"),
            ],
        )

        # case1: status is "success"
        # Arrange
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        actual_result = job.result()

        # Assert
        assert actual_result.counts == {0: 490, 1: 10, 2: 20, 3: 480}

        # case2: status is "failure"
        # Arrange
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        actual_wfc = job.wait_for_completion()

        # Assert
        assert actual_wfc is not None

        # case3: status is "cancelled"
        # Arrange
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        actual_wfc = job.wait_for_completion()

        # Assert
        assert actual_wfc is not None

    def test_result__wait(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            side_effect=[
                get_dummy_job("running"),
                get_dummy_job("succeeded"),
            ],
        )

        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act
        start_time = time.time()
        actual = job.result(wait=3.0)
        elapsed_time = time.time() - start_time

        # Assert
        assert actual.counts == {0: 490, 1: 10, 2: 20, 3: 480}
        assert elapsed_time >= 3.0

    def test_result__timeout(self, mocker: MockerFixture):
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            side_effect=[
                get_dummy_job("running"),
                get_dummy_job("running"),
                get_dummy_job("running"),
                get_dummy_job("running"),
                get_dummy_job("running"),
            ],
        )

        # Arrange
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())
        assert job.status == "running"

        # Act & Assert
        with pytest.raises(BackendError):
            job.result(timeout=10.0, wait=3.0)

    def test_cancel(self, mocker: MockerFixture):
        # Arrange
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.cancel_job",
            return_value=None,
        )
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            return_value=get_dummy_job("cancelled"),
        )
        job_raw = get_dummy_job("running")
        job = OqtopusSamplingJob(job=job_raw, job_api=JobApi())

        # Act
        job.cancel()

        # Assert
        mock_obj.assert_called_once_with("dummy_job_id")


class TestOqtopusConfig:
    def test_init_error(self):
        # case: counts does not exist in result
        result_dict = {}
        with pytest.raises(ValueError, match="'counts' does not exist in result"):
            OqtopusSamplingResult(result_dict)

    def test_from_file(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("builtins.open", mock_open(read_data=config_file_data))

        # Act
        actual = OqtopusConfig.from_file()

        # Assert
        assert actual.url == "default_url"
        assert actual.api_token == "default_api_token"  # noqa: S105
        assert actual.proxy is None

    def test_from_file__section(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("builtins.open", mock_open(read_data=config_file_data))

        # Act
        actual = OqtopusConfig.from_file(section="test")

        # Assert
        assert actual.url == "test_url"
        assert actual.api_token == "test_api_token"  # noqa: S105
        assert actual.proxy is None

    def test_from_file__optional(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("builtins.open", mock_open(read_data=config_file_data))

        # Act
        actual = OqtopusConfig.from_file(section="option")

        # Assert
        assert actual.url == "test_url"
        assert actual.api_token == "test_api_token"  # noqa: S105
        assert actual.proxy == "https://testproxy:port"

    def test_from_file_sse_container(self):
        # Act
        with patch.dict("os.environ", {"OQTOPUS_ENV": "sse_container"}):
            actual = OqtopusConfig.from_file()

        # Assert
        assert actual.url == ""
        assert actual.api_token == ""
        assert actual.proxy is None

    def test_from_file__wrong(self, mocker: MockerFixture):
        # Arrange
        mocker.patch("builtins.open", mock_open(read_data=config_file_data))

        # case: section is not found
        # Act & Assert
        with pytest.raises(KeyError):
            OqtopusConfig.from_file(section="not found")

        # case: api_key is not found
        # Act & Assert
        with pytest.raises(KeyError):
            OqtopusConfig.from_file(section="wrong")

    def test_properties(self):
        # Act
        actual = OqtopusConfig("dummy_url", "dummy_api_token", "https://dummy:1234")

        # Assert
        assert actual.url == "dummy_url"
        assert actual.api_token == "dummy_api_token"  # noqa: S105
        assert actual.proxy == "https://dummy:1234"


class TestOqtopusSamplingBackend:
    def test_init__use_env(self, mocker: MockerFixture):
        # Arrange
        def mock_getenv(key: str, default: str | None = None) -> str | None:
            if key == "OQTOPUS_URL":
                return "dummy_url"
            if key == "OQTOPUS_API_TOKEN":
                return "dummy_api_token"
            if key == "OQTOPUS_PROXY":
                return "https://dummy:1234"
            return default

        mocker.patch("os.getenv", side_effect=mock_getenv)

        # Act
        backend = OqtopusSamplingBackend()

        # Assert
        api_client = backend._job_api.api_client  # noqa: SLF001
        assert api_client.configuration.host == "dummy_url"
        assert api_client.default_headers["q-api-token"] == "dummy_api_token"
        assert api_client.configuration.proxy == "https://dummy:1234"

    def test_init__not_use_env(self, mocker: MockerFixture):
        # Arrange
        def mock_getenv(key: str, default: str | None = None) -> str | None:
            if key == "OQTOPUS_URL":
                return "dummy_url"
            # OQTOPUS_API_TOKEN isn't set
            # elif key == "OQTOPUS_API_TOKEN":
            #     return "dummy_api_token"
            if key == "OQTOPUS_PROXY":
                return "https://dummy:1234"
            return default

        mocker.patch("os.getenv", side_effect=mock_getenv)
        mocker.patch(
            "quri_parts_oqtopus.backend.OqtopusConfig.from_file",
            return_value=OqtopusConfig("fake_url", "fake_token", "https://fake_proxy"),
        )

        # Act
        backend = OqtopusSamplingBackend()

        # Assert
        api_client = backend._job_api.api_client  # noqa: SLF001
        assert api_client.configuration.host == "fake_url"
        assert api_client.default_headers["q-api-token"] == "fake_token"
        assert api_client.configuration.proxy == "https://fake_proxy"

    def test_sample(self, mocker: MockerFixture):
        # Arrange
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.submit_job",
            return_value=JobsSubmitJobResponse(job_id="dummy_job_id"),
        )
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            return_value=get_dummy_job(),
        )
        backend = OqtopusSamplingBackend(get_dummy_config())

        circuit = QuantumCircuit(2)
        circuit.add_H_gate(0)
        circuit.add_CNOT_gate(0, 1)

        # Act
        job = backend.sample(
            circuit,
            device_id="dummy_device_id",
            shots=1000,
            name="dummy_name",
            description="dummy_description",
            transpiler_info={
                "transpiler_lib": "qiskit",
                "transpiler_options": {"optimization_level": 2},
            },
        )

        # Assert
        assert job.job_id == "dummy_job_id"
        assert job.name == "dummy_name"
        assert job.description == "dummy_description"
        assert job.job_type == "sampling"
        assert job.status == "succeeded"
        assert job.device_id == "demmy_device_id"
        assert job.shots == 1000
        assert job.job_info["program"] == [
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;'  # noqa: E501
        ]
        assert (
            job.job_info["transpile_result"]["transpiled_program"]
            == 'OPENQASM 3; include "stdgates.inc"; qubit[2] q; bit[2] c; rz(1.5707963267948932) q[0]; sx q[0]; rz(1.5707963267948966) q[0]; cx q[0], q[1]; c = measure q;'  # noqa: E501
        )
        assert job.result().counts == {0: 490, 1: 10, 2: 20, 3: 480}
        assert job.transpiler_info == {
            "transpiler_lib": "qiskit",
            "transpiler_options": {"optimization_level": 2},
        }
        assert job.simulator_info == {}
        assert job.mitigation_info == {}
        assert job.execution_time == 5.123
        assert job.submitted_at == datetime.datetime(2000, 1, 2, 3, 4, 1)  # noqa: DTZ001
        assert job.ready_at == datetime.datetime(2000, 1, 2, 3, 4, 2)  # noqa: DTZ001
        assert job.running_at == datetime.datetime(2000, 1, 2, 3, 4, 3)  # noqa: DTZ001
        assert job.ended_at == datetime.datetime(2000, 1, 2, 3, 4, 4)  # noqa: DTZ001
        mock_obj.assert_called_once_with(body=get_dummy_JobsSubmitJobRequest())

    def test_sample_circuit_array(self, mocker: MockerFixture):
        # Arrange
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.submit_job",
            return_value=JobsSubmitJobResponse(job_id="dummy_job_id"),
        )
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            return_value=get_dummy_multimanual_job(),
        )
        backend = OqtopusSamplingBackend(get_dummy_config())

        circuit = QuantumCircuit(2)
        circuit.add_H_gate(0)
        circuit.add_CNOT_gate(0, 1)

        circuit2 = QuantumCircuit(3)
        circuit2.add_H_gate(0)
        circuit2.add_CNOT_gate(0, 1)
        circuit2.add_RY_gate(2, 0.1)

        # Act
        job = backend.sample(
            [circuit, circuit2, circuit],
            device_id="dummy_device_id",
            shots=1000,
            name="dummy_name",
            description="dummy_description",
            transpiler_info={
                "transpiler_lib": "qiskit",
                "transpiler_options": {"optimization_level": 2},
            },
        )

        # Assert
        assert job.job_id == "dummy_job_id"
        program = [
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;',  # noqa: E501
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[3] q;\nbit[3] c;\n\nh q[0];\ncx q[0], q[1];\nry(0.1) q[2];\nc = measure q;',  # noqa: E501
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;',  # noqa: E501
        ]
        mock_obj.assert_called_once_with(
            body=get_dummy_JobsSubmitJobRequest(
                job_type="multi_manual", program=program
            )
        )
        assert job.result().counts == {0: 490, 1: 10, 6: 20, 15: 480}
        assert job.result().divided_counts == {
            0: {0: 490, 1: 10, 2: 20, 3: 480},
            1: {0: 500, 1: 20, 3: 480},
        }

    def test_sample_qasm(self, mocker: MockerFixture):
        # Arrange
        mock_obj = mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.submit_job",
            return_value=JobsSubmitJobResponse(job_id="dummy_job_id"),
        )
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            return_value=get_dummy_job(),
        )
        backend = OqtopusSamplingBackend(get_dummy_config())

        # Act
        job = backend.sample_qasm(
            qasm_data_with_measure,
            device_id="dummy_device_id",
            shots=1000,
            name="dummy_name",
            description="dummy_description",
            transpiler_info={
                "transpiler_lib": "qiskit",
                "transpiler_options": {"optimization_level": 2},
            },
        )

        # Assert
        assert job.job_id == "dummy_job_id"
        mock_obj.assert_called_once_with(body=get_dummy_JobsSubmitJobRequest())

    def test_sample_qasm_sse_container(self):
        # Arrange
        class MockSSESampler:
            def req_transpile_and_exec(
                self, program: list[str], shots: int, transpiler_info: dict
            ) -> JobsSubmitJobResponse:
                self.program = program
                self.shots = shots
                self.transpiler_info = transpiler_info
                return JobsSubmitJobResponse(job_id="dummy_job_id")

            def assertion(
                self, program: list[str], shots: int, transpiler_info: dict
            ) -> None:
                assert self.program == program
                assert self.shots == shots
                assert self.transpiler_info == transpiler_info

        # mock sse_sampler
        mock_obj = MockSSESampler()
        sys.modules["sse_sampler"] = mock_obj
        backend = OqtopusSamplingBackend(get_dummy_config())

        # Act
        with patch.dict("os.environ", {"OQTOPUS_ENV": "sse_container"}):
            job = backend.sample_qasm(
                qasm_data_with_measure,
                device_id="dummy_device_id",
                shots=1000,
                name="dummy_name",
                description="dummy_description",
                transpiler_info={
                    "transpiler_lib": "qiskit",
                    "transpiler_options": {"optimization_level": 2},
                },
            )

        # Assert
        assert job.job_id == "dummy_job_id"
        mock_obj.assertion(
            program=[qasm_data_with_measure],
            shots=1000,
            transpiler_info={
                "transpiler_lib": "qiskit",
                "transpiler_options": {"optimization_level": 2},
            },
        )

    def test_retrieve_job(self, mocker: MockerFixture):
        # Arrange
        mocker.patch(
            "quri_parts_oqtopus.rest.JobApi.get_job",
            return_value=get_dummy_job(),
        )
        backend = OqtopusSamplingBackend(get_dummy_config())

        # Act
        job = backend.retrieve_job("dummy_job_id")

        # Assert
        assert type(job) is OqtopusSamplingJob
        assert job.job_id == "dummy_job_id"
        assert job.name == "dummy_name"
        assert job.description == "dummy_description"
        assert job.job_type == "sampling"
        assert job.status == "succeeded"
        assert job.device_id == "demmy_device_id"
        assert job.shots == 1000
        assert job.job_info["program"] == [
            'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc = measure q;'  # noqa: E501
        ]
        assert (
            job.job_info["transpile_result"]["stats"]
            == '{"before": {"n_qubits": 2, "n_gates": 4, "n_gates_1q": 3, "n_gates_2q": 1, "depth": 4}, "after": {"n_qubits": 6, "n_gates": 4, "n_gates_1q": 3, "n_gates_2q": 1, "depth": 4}}'  # noqa: E501
        )
        assert (
            job.job_info["transpile_result"]["transpiled_program"]
            == 'OPENQASM 3; include "stdgates.inc"; qubit[2] q; bit[2] c; rz(1.5707963267948932) q[0]; sx q[0]; rz(1.5707963267948966) q[0]; cx q[0], q[1]; c = measure q;'  # noqa: E501
        )
        assert (
            job.job_info["transpile_result"]["virtual_physical_mapping"]
            == '{"0": 0, "1": 1}'
        )
        assert job.result().counts == {0: 490, 1: 10, 2: 20, 3: 480}
        assert job.transpiler_info == {
            "transpiler_lib": "qiskit",
            "transpiler_options": {"optimization_level": 2},
        }
        assert job.simulator_info == {}
        assert job.mitigation_info == {}
        assert job.execution_time == 5.123
        assert job.submitted_at == datetime.datetime(2000, 1, 2, 3, 4, 1)  # noqa: DTZ001
        assert job.ready_at == datetime.datetime(2000, 1, 2, 3, 4, 2)  # noqa: DTZ001
        assert job.running_at == datetime.datetime(2000, 1, 2, 3, 4, 3)  # noqa: DTZ001
        assert job.ended_at == datetime.datetime(2000, 1, 2, 3, 4, 4)  # noqa: DTZ001
